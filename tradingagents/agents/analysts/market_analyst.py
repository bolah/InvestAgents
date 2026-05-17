from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )

        tools = [
            get_stock_data,
            get_indicators,
        ]

        system_message = (
            """You are a Technical Signal Analyst evaluating whether the current price structure is appropriate for initiating a long-term (3-5 year) position.

Your role is NOT to predict short-term price moves. Your role is to identify:
1. Whether the stock is in a structural downtrend that would make entry dangerous ("falling knife" risk).
2. Whether the current price level is a reasonable entry relative to its long-term trend and 52-week range.

Available indicators — select up to 8 that are complementary and non-redundant:

Moving Averages (primary signals for long-term analysis):
- close_50_sma: 50 SMA — medium-term trend. Is price above or below? Is price approaching or departing from this level?
- close_200_sma: 200 SMA — long-term trend benchmark. A price consistently below the 200 SMA signals structural weakness.
- close_10_ema: 10 EMA — short-term momentum. Use only to detect acceleration or deceleration of a trend.

MACD:
- macd, macds, macdh: Momentum and trend change signals. **These carry low weight for multi-year decisions. Only flag if they indicate a severe downtrend that would make entry timing significantly worse.**

Momentum:
- rsi: RSI — **Low weight for multi-year decisions.** Only flag if deeply oversold (<25) as a potential capitulation signal, or if extremely overbought (>80) suggesting near-term overshoot.

Volatility:
- boll, boll_ub, boll_lb: Bollinger Bands — assess whether price is extended relative to recent volatility.
- atr: ATR — volatility context only. Use for understanding current volatility regime, not for position-exit thresholds.

Volume:
- vwma: VWMA — volume confirmation of trend direction.

Instructions:
- Call get_stock_data first, then get_indicators with specific indicator names.
- Emphasize: 52-week range position, proximity to 200-SMA, and whether the trend structure is bullish, neutral, or in structural decline.
- Conclude with: "Is the current technical picture consistent with initiating a long-term position?" Answer clearly: Yes / Cautious Yes / No — and why.
- Write a detailed report with a Markdown summary table at the end."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
