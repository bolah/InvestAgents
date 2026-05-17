from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        asset_type = state.get("asset_type", "stock")
        asset_label = "company" if asset_type == "stock" else "asset"
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )
        config = get_config()
        lookback_days = config.get("news_lookback_days", 180)

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            f"You are a structural news researcher evaluating events and trends relevant to a long-term (3-5 year) investment in this {asset_label}. "
            f"Use get_news for {asset_label}-specific news searches and get_global_news for macroeconomic context. "
            f"Use a lookback window of approximately {lookback_days} days. "
            "Focus exclusively on structural, durable signals: "
            "(1) Regulatory shifts or legal developments that could affect the business model; "
            "(2) Competitive disruptions — new entrants, M&A activity, product obsolescence risks; "
            "(3) Macro tailwinds or headwinds — interest rate sensitivity, commodity exposure, geopolitical exposure; "
            "(4) Management changes — CEO/CFO turnover, board composition, insider buying or selling patterns; "
            "(5) Capital structure events — large acquisitions, spin-offs, major debt issuances. "
            "Do NOT report on: day-to-day price moves, short-term earnings beats/misses, analyst upgrades/downgrades unless they reflect a thesis change. "
            "Frame every finding in terms of: does this change the 3-5 year outlook for this business? "
            "Provide a comprehensive narrative report with a Markdown summary table at the end."
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
            "news_report": report,
        }

    return news_analyst_node
