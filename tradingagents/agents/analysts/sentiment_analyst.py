"""Sentiment analyst — multi-source sentiment analysis for a target ticker.

Previously named ``social_media_analyst``. Renamed and redesigned because
the old version had a prompt that demanded social-media analysis but the
only tool available was Yahoo Finance news — which led LLMs to fabricate
Reddit/X/StockTwits content under prompt pressure (verified live).

The redesigned agent pre-fetches three complementary data sources before
the LLM is invoked and injects them into the prompt as structured blocks:

  1. News headlines     — Yahoo Finance (institutional framing)
  2. StockTwits messages — retail-trader posts indexed by cashtag, with
                           user-labeled Bullish/Bearish sentiment tags
  3. Reddit posts        — r/wallstreetbets, r/stocks, r/investing

The agent does not use tool-calling; the data is in the prompt from
turn 0. The LLM produces the sentiment report in a single invocation.

See: https://github.com/TauricResearch/TradingAgents/issues/557
"""

from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.reddit import fetch_reddit_posts
from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages


def _lookback_start(trade_date: str, days: int) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")


def create_sentiment_analyst(llm):
    """Create a sentiment analyst node for the trading graph.

    Pre-fetches news + StockTwits + Reddit data, injects them into the
    prompt as structured blocks, and produces a sentiment report in a
    single LLM call.
    """

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        end_date = state["trade_date"]
        config = get_config()
        lookback_days = config.get("sentiment_lookback_days", 90)
        start_date = _lookback_start(end_date, lookback_days)
        instrument_context = build_instrument_context(ticker)

        # Pre-fetch all three sources. Each fetcher degrades gracefully and
        # returns a string (no exceptions surface from here), so the LLM
        # always sees something — either real data or a clear placeholder.
        news_block = get_news.func(ticker, start_date, end_date)
        stocktwits_block = fetch_stocktwits_messages(ticker, limit=30)
        reddit_block = fetch_reddit_posts(ticker)

        system_message = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            news_block=news_block,
            stocktwits_block=stocktwits_block,
            reddit_block=reddit_block,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    "\n{system_message}\n"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=end_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        # No bind_tools — the data is already in the prompt; a single LLM
        # call produces the report directly.
        chain = prompt | llm
        result = chain.invoke(state["messages"])

        return {
            "messages": [result],
            "sentiment_report": result.content,
        }

    return sentiment_analyst_node


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    news_block: str,
    stocktwits_block: str,
    reddit_block: str,
) -> str:
    """Assemble the stakeholder-narrative system message with structured data blocks."""
    return f"""You are a Stakeholder & Narrative Analyst. Your task is to identify the **enduring narrative** the market has about {ticker} and whether that narrative is shifting — using three pre-fetched data sources covering {start_date} to {end_date}.

Short-term sentiment fluctuations (single-day reactions, earnings beats/misses) are noise at a 3-5 year investment horizon. Focus only on durable narrative changes that could affect long-term positioning.

## Data sources (pre-fetched)

### News headlines — Yahoo Finance
Institutional framing. What themes keep recurring? What has changed structurally?

<start_of_news>
{news_block}
<end_of_news>

### StockTwits messages — retail-trader sentiment
Each message carries a user-labeled tag (Bullish / Bearish / no-label).

<start_of_stocktwits>
{stocktwits_block}
<end_of_stocktwits>

### Reddit posts — r/wallstreetbets, r/stocks, r/investing
Community discussion. Engagement via upvote score and comment count matters.

<start_of_reddit>
{reddit_block}
<end_of_reddit>

## What to look for

1. **Dominant narrative**: What is the prevailing long-term story the market tells about this company? (e.g., "AI infrastructure winner", "legacy tech disruption risk", "reliable compounder")
2. **Narrative shifts**: Is the dominant narrative changing direction? Is there a new theme emerging across sources that wasn't present 3-6 months ago?
3. **Stakeholder confidence**: Do insiders, institutional commentary, and retail sentiment broadly align or diverge on the long-term outlook?
4. **Cross-source divergences**: If institutional news frames the company one way and retail sentiment frames it another, that divergence is itself a signal.
5. **Long-term catalysts and risks** identified in discourse: not earnings surprise reactions, but structural concerns about competition, regulation, or business model durability.

## What to ignore
- Single-day price reactions to earnings, macro events, or analyst upgrades/downgrades
- Short-term StockTwits/Reddit momentum chasing or "to the moon" commentary
- Any sentiment signal with a horizon shorter than 1 year

## Output
1. **Dominant narrative** for {ticker}: what is it and is it strengthening or weakening?
2. **Source-by-source breakdown** with specific evidence (cite message counts, key posts/headlines).
3. **Narrative shifts** detected: what has changed vs. the apparent prior narrative?
4. **Long-term catalysts and risks** surfaced by stakeholder discourse.
5. **Markdown table** at the end summarizing narrative themes, their direction, and evidence.

{get_language_instruction()}"""


# ---------------------------------------------------------------------------
# Backwards-compatibility shim
# ---------------------------------------------------------------------------
def create_social_media_analyst(llm):
    """Deprecated alias for :func:`create_sentiment_analyst`.

    Kept so existing code that imports ``create_social_media_analyst``
    continues to work.

    .. deprecated::
        Import :func:`create_sentiment_analyst` directly instead.
    """
    import warnings
    warnings.warn(
        "create_social_media_analyst is deprecated and will be removed in a "
        "future version. Use create_sentiment_analyst instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_sentiment_analyst(llm)
