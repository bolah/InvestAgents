"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import InvestmentProposal, render_trader_proposal
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, InvestmentProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(company_name, asset_type)
        investment_plan = state["investment_plan"]
        investment_horizon = state.get("investment_horizon", "3-5 years")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an investment analyst translating a research team's investment plan "
                    f"into a concrete investment decision for a long-term ({investment_horizon}) horizon. "
                    "Based on your analysis, provide a specific recommendation to buy, sell, or hold. "
                    "Anchor your reasoning in the analysts' reports and the research plan. "
                    "Your conviction score must reflect the quality and clarity of the long-term thesis, "
                    "not short-term price predictions."
                    + get_language_instruction()
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Based on a comprehensive analysis by a team of analysts, here is an investment "
                    f"plan tailored for {company_name}. {instrument_context} This plan incorporates "
                    f"insights from technical positioning, fundamental quality, valuation, competitive moat, "
                    f"macro/secular trends, stakeholder narrative, and news analysis. Use this plan as "
                    f"a foundation for evaluating the long-term investment decision.\n\n"
                    f"Proposed Investment Plan: {investment_plan}\n\n"
                    f"Provide your investment decision with conviction score, thesis horizon, and key catalysts."
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
