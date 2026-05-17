# tradingagents/agents/analysts/valuation_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_language_instruction,
)
from tradingagents.agents.utils.core_stock_tools import (
    get_valuation_multiples,
)


def create_valuation_analyst(llm):
    def valuation_analyst_node(state):
        current_date = state["trade_date"]
        investment_horizon = state.get("investment_horizon", "3-5 years")
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(state["company_of_interest"], asset_type)

        tools = [
            get_valuation_multiples,
            get_income_statement,
            get_balance_sheet,
            get_cashflow,
        ]

        system_message = (
            f"You are a Valuation Analyst specializing in long-term investment analysis with a {investment_horizon} horizon. "
            "Your job is to assess whether a stock is cheap, fair, or expensive relative to its own historical multiples and business quality. "
            "Use get_valuation_multiples for current P/E, P/FCF, EV/EBITDA figures. "
            "Use get_income_statement, get_balance_sheet, and get_cashflow for annual financial data to establish 5-year context. Always pass freq='annual' when calling these tools. "
            "Answer: Is the current multiple justified by the business quality and growth trajectory? "
            "What is the primary valuation driver (earnings growth expectations, margin expansion, multiple re-rating)? "
            "Is the stock pricing in an optimistic or pessimistic scenario relative to its history? "
            "Conclude with a clear valuation verdict: Cheap / Fair / Expensive — and why. "
            "Append a Markdown table at the end summarizing key valuation metrics."
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
            "valuation_report": report,
        }

    return valuation_analyst_node
