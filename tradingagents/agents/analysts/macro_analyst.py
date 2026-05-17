# tradingagents/agents/analysts/macro_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.web_tools import web_search_tool


def create_macro_analyst(llm):
    def macro_analyst_node(state):
        current_date = state["trade_date"]
        investment_horizon = state.get("investment_horizon", "3-5 years")
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )

        tools = [web_search_tool]

        system_message = (
            f"You are a Macro & Secular Analyst identifying {investment_horizon} industry tailwinds and headwinds "
            "for the company's sector. "
            "Use web_search_tool to research qualitative industry context. "
            "Focus on: "
            "(1) Secular demographic and behavioral shifts affecting the industry; "
            "(2) Regulatory trajectory — is the regulatory environment becoming more or less favorable?; "
            "(3) Technological disruption potential — is the company's core business model at risk from AI, automation, or platform shifts?; "
            "(4) Competitive intensity trends — is the industry consolidating or fragmenting?; "
            "(5) Macro sensitivity — interest rate exposure, commodity dependency, FX risk for global businesses. "
            "IMPORTANT: Do NOT cite specific financial figures (revenue, earnings, price targets) from web results. "
            "Use web results only for qualitative industry narrative. All quantitative figures must come from structured data tools. "
            "Conclude with: a ranked list of the top 3 tailwinds and top 3 headwinds for the next 3-5 years. "
            "Append a Markdown table summarizing secular trends."
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
            "macro_report": report,
        }

    return macro_analyst_node
