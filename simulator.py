from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
import pandas as pd
from pydantic import BaseModel, Field
import csv


def getExampleDialogue(index: int) -> str:
    pass

def getIntentDialogue(index: int) -> str:
    dialogue_lines = []

    with open("./intent dialogues.csv", mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if int(row["index"]) == index:
                dialogue_lines.append(f"{row['role']}: {row['message']}")

    dialogue_lines.append("USER: <COMPLETE_CONVERSATION>")

    return "\n".join(dialogue_lines)


def getLLMDialogue(index: int) -> str:
    dialogue_lines = []

    with open("./llm dialogues.csv", mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if int(row["index"]) == index:
                dialogue_lines.append(f"{row['role']}: {row['message']}")

    dialogue_lines.append("USER: <COMPLETE_CONVERSATION>")

    return "\n".join(dialogue_lines)


async def agentResponse(index: int, conversation_history: str) -> str:
    example_dialogue = getExampleDialogue(index) # implement the function that fits to your example dialogue file

    llm = ChatOpenAI(model="gpt-4o", temperature=1)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are a USER chatting with a chatbot.
    Your role is to make a USER response to continue the "current conversation".
    You should behave like a USER of the "example dialogue".
    You MUST answer in KOREAN.
    
    [Context]
    - example dialogue: 
    {example_dialogue}
    - current conversation: 
    {conversation_history}
    """
    )

    chain = prompt_template | llm
    response = chain.invoke(
        {
            "example_dialogue": example_dialogue,
            "conversation_history": conversation_history + "\nUSER: ",
        }
    )

    return response.content


class EvalOutput(BaseModel):
    score1: int = Field(
        description="The evaluation score for dialogue 1. It should be an integer from 1 to 5."
    )
    reason1: str = Field(
        description="Briefly explain the reason why you rate the score1."
    )
    score2: int = Field(
        description="The evaluation score for dialogue 2. It should be an integer from 1 to 5."
    )
    reason2: str = Field(
        description="Briefly explain the reason why you rate the score1."
    )


def autoEvaluation(index) -> EvalOutput:
    dialogue1 = getIntentDialogue(index)
    dialogue2 = getLLMDialogue(index)

    # llm = ChatOpenAI(model="gpt-4o", temperature=1)
    # llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=1)
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=1)
    llm = llm.with_structured_output(EvalOutput)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are an evaluator for testing naturalness of the chatbot responses.
    Given the following dialogues between chatbot and user, evaluate the naturalness of each chatbot.
    
    [Instruction]
    This metric measures the resemblance to humans.
    Based on the criteria below, evaluate the chatbot’s overall performance and assign a score from 1 to 5, where 5 represents most likely to be human.
    Additionally, provide a brief explanation for your rating.
    
    Evaluation Criteria:
    1: The speaker continuously repeats itself, typical robotic behavior. Or the speech is hard to understand.
    2: The speaker repeats itself occasionally, the vocabulary is limited, like a robot.
    3: The speaker does not have repeated behaviors (unless for verifying information). Vocabulary is enough to communicate effectively, speech is easy to understand. But I am confident that humans rarely speak like this.
    4: The speaker is likely to be a human. There is rarely logical inconsistency. But from some details I feel like the utterance is a bit weird and somewhat resembles AI.
    5: Can not really tell if this is AI or human. Human could probably say the same thing in real life. 
  
    Make sure that you are NOT evaluating USER's response. You are only evaluating AI's response.
    You MUST answer in ENGLISH.
    
    [Context]
    - Dialogue 1:
    {dialogue1}
    - Dialogue 2:
    {dialogue2}
    """
    )

    chain = prompt_template | llm
    response = chain.invoke(
        {
            "dialogue1": dialogue1,
            "dialogue2": dialogue2,
        }
    )

    return response
