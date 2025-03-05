from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Any
from phasemanager import PhaseManager


async def selectTopic(phase_manager: PhaseManager, conversation_history: str) -> Any:
    bot_name, bot_desc = phase_manager.getBotInfo()
    actions = phase_manager.getTopics()
    phase_info = phase_manager.getCurrPhase().getInfo()
    response_format = phase_manager.getCurrPhase().getResponseFormat()

    llm = ChatOpenAI(model="gpt-4o", temperature=1)
    llm = llm.with_structured_output(response_format)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are an action selector of the {bot_name}, which is {bot_desc}. 
    Your role is to do two things with reference to the "Context".
    1. Decide whether the main goal of the current phase is achieved. And if it is achieved, select which phase to go next.
    2. Decide which action to use for the current conversation turn. You can only select one action from the available actions below.
    
    [Context]
    - current phase name: {phase_name}
    - current phase goal: {phase_goal}
    - available actions: {phase_actions}
    - current phase instruction: {phase_instruction}
    - conversation history: {conversation_history}
    """
    )

    chain = prompt_template | llm
    response = await chain.ainvoke(
        {
            "bot_name": bot_name,
            "bot_desc": bot_desc,
            "phase_name": phase_info["name"],
            "phase_goal": phase_info["goal"],
            "phase_actions": actions,
            "phase_instruction": phase_info["instruction"],
            "conversation_history": conversation_history,
        }
    )

    return response


async def generateResponse(
    phase_manager: PhaseManager,
    conversation_history: str,
    action: str,
    action_reason: str,
) -> str:
    bot_name, bot_desc = phase_manager.getBotInfo()
    phase_info = phase_manager.getCurrPhase().getInfo()
    
    llm = ChatOpenAI(model="gpt-4o", temperature=1)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are a response generator of the {bot_name}, which is {bot_desc}.
    To achieve the "phase goal" within the total conversation, one "action" is selected for the current conversation turn.
    Your role is to make a chatbot response for this turn according to the "Context".
    You MUST ask or respond about one subject at a time.
    The response MUST be in KOREAN.
    
    [Context]
    - current phase name: {phase_name}
    - current phase goal: {phase_goal}
    - selected action: {action}
    - reason for the action selection: {action_reason}
    - conversation history: {conversation_history}
    """
    )

    chain = prompt_template | llm
    response = await chain.ainvoke(
        {
            "bot_name": bot_name,
            "bot_desc": bot_desc,
            "phase_name": phase_info["name"],
            "phase_goal": phase_info["goal"],
            "action": action,
            "action_reason": action_reason,
            "conversation_history": conversation_history + "\nAI: ",
        }
    )

    return response


async def executeChatbot(
    phase_manager: PhaseManager, conversation_history: str
) -> tuple[str, bool]:
    selector_response = await selectTopic(phase_manager, conversation_history)
    
    # next_phase_info = ""
    # if selector_response.next_phase:
    #     next_phase_info += f"\n- next phase name: {selector_response.next_phase}"
    #     next_phase_info += f"\n- next phase reason: {selector_response.next_phase_reason}"
        
    chatbot_response = await generateResponse(
        phase_manager,
        conversation_history,
        phase_manager.getTopics()[selector_response.action],
        selector_response.action_reason,
        # next_phase_info,
    )
    changed = phase_manager.goNextPhase(selector_response.next_phase)

    return chatbot_response.content, changed
