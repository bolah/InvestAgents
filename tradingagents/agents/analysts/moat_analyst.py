# tradingagents/agents/analysts/moat_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_language_instruction,
)
from tradingagents.agents.utils.core_stock_tools import get_quality_metrics


def create_moat_analyst(llm):
    def moat_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_quality_metrics,
            get_income_statement,
            get_balance_sheet,
            get_cashflow,
        ]

        system_message = (
            "You are a Moat & Quality Analyst evaluating the long-term competitive durability of a business. "
            "Use get_quality_metrics for gross margin trends, FCF conversion, and capex intensity. "
            "Use get_income_statement, get_balance_sheet, and get_cashflow for annual financial data. "
            "Answer these questions: "
            "(1) Does this business earn above its cost of capital consistently? (Look at returns on capital, not just net income.) "
            "(2) Are gross margins improving, stable, or deteriorating — and why? "
            "(3) What structural advantage sustains this business? Identify the moat type: "
            "switching costs, network effects, cost advantage, brand/intangibles, efficient scale, or none. "
            "(4) What are the primary threats to this moat over the next 3-5 years? "
            "(Technological disruption, competitive intensity, regulatory risk, margin pressure.) "
            "Conclude with a moat rating: Wide / Narrow / None — and a confidence level. "
            "Append a Markdown table summarizing quality metrics."
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
            "moat_report": report,
        }

    return moat_analyst_node
