import argparse
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import csv
import os

from phasemanager import PhaseManager
from phase import Phase
from DB import initialize, addMessage, getHistory, reset, saveConversation
from chatbot import executeChatbot
from simulator import agentResponse, autoEvaluation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    initialize()

    # reset DB
    reset()

    yield


# Set FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class routerData(BaseModel):
    criteria: str
    next_phase: str


class phaseData(BaseModel):
    name: str
    goal: str
    action_list: list[str]
    instruction: str
    router_list: list[routerData]


class actionData(BaseModel):
    action_name: str
    action_explanation: str


class chatbotSettingData(BaseModel):
    bot_name: str
    bot_desc: str
    start_phase: str
    finish_phases: list[str]
    phases: list[phaseData]
    actions: list[actionData]


class userInputData(BaseModel):
    input: str


# =================================================================================================================================================
# API Server Code
# =================================================================================================================================================

# save chatbot setting
@app.post("/save-settings")
def saveSetting(data: chatbotSettingData):
    phase_manager = PhaseManager(data.bot_name, data.bot_desc)
    app.state.phase_manager = phase_manager
    try:
        for phase in data.phases:
            print(f"{phase.name} adding...")
            dict_router_list = [router.model_dump() for router in phase.router_list]
            new_phase = Phase(
                phase.name,
                phase.goal,
                phase.action_list,
                phase.instruction,
                dict_router_list,
            )
            phase_manager.addNewPhase(new_phase)

        phase_manager.addNewPhase(Phase("FINISH", "", [], "", []))
        phase_manager.setStartPhase(data.start_phase)
        phase_manager.setCurrPhase(data.start_phase)
        print(f"current phase: {data.start_phase}")
        # reset DB for new chatbot
        reset()
        addMessage("PHASE", data.start_phase)

        action_dict = {}
        for action in data.actions:
            action_dict[action.action_name] = action.action_explanation
        print(phase_manager.updateTopics(action_dict))

        return {
            "status": "success",
            "result": f"Chatbot named {data.bot_name} set completely.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# execute one conversation with the user input
@app.post("/execute")
async def execute(user_input: userInputData):
    phase_manager = app.state.phase_manager
    if phase_manager == None:
        raise HTTPException(status_code=400, detail="No Chatbot Saved.")
    input = user_input.input
    addMessage("USER", input)
    conversation_history = getHistory()
    try:
        response, changed = await executeChatbot(phase_manager, conversation_history)
        addMessage("AI", response)
        if changed:
            addMessage("PHASE", phase_manager.getCurrPhase().getName())
        if phase_manager.getCurrPhase().getName() == "FINISH":
            finished = True
        else:
            finished = False
        return {"status": "success", "message": response, "finished": finished}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# reset the conversation
@app.post("/reset-DB")
def resetDB():
    try:
        reset()
        start_phase_name = app.state.phase_manager.getStartPhase().getName()
        app.state.phase_manager.setCurrPhase(start_phase_name)
        addMessage("PHASE", start_phase_name)
        return {"status": "success", "result": "All chatbot setting initialized."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def main():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

    return


# =================================================================================================================================================
# Local Test & Evaluation Code
# =================================================================================================================================================


# get setting data from yaml file
def getTestSettingData() -> chatbotSettingData:
    try:
        with open("./LLM-Cumpa Specification.yaml", "r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)

        data = chatbotSettingData.model_validate(yaml_data)

    except FileNotFoundError:
        print("file not found")

    except ValidationError as e:
        print(f"setting data validation failed: {e}")

    return data


# save chatbot setting for test
def saveTestSetting(data: chatbotSettingData) -> PhaseManager:
    phase_manager = PhaseManager(data.bot_name, data.bot_desc)

    for phase in data.phases:
        # print(f"{phase.name} adding...")
        dict_router_list = [router.model_dump() for router in phase.router_list]
        new_phase = Phase(
            phase.name,
            phase.goal,
            phase.action_list,
            phase.instruction,
            dict_router_list,
        )
        phase_manager.addNewPhase(new_phase)

    phase_manager.addNewPhase(Phase("FINISH", "", [], "", []))
    phase_manager.setStartPhase(data.start_phase)
    phase_manager.setCurrPhase(data.start_phase)
    # print(f"current phase: {data.start_phase}")
    # reset DB for new chatbot
    reset()
    addMessage("PHASE", data.start_phase)

    action_dict = {}
    for action in data.actions:
        action_dict[action.action_name] = action.action_explanation
    # print(phase_manager.updateTopics(action_dict))
    phase_manager.updateTopics(action_dict)

    return phase_manager


# automated testing with user agent
async def autoTest(phase_manager: PhaseManager):
    for index in range(1, 51):
        while True:
            # make chatbot response
            response, changed = await executeChatbot(phase_manager, getHistory())
            
            # finish the dialogue if the next phase is FINISH
            if phase_manager.getCurrPhase().getName() == "FINISH":
                # print("AI: " + response)
                addMessage("AI", response)
                break
            
            # if there is no phase change, use generated output
            if not changed:
                # print("AI: " + response)
                addMessage("AI", response)
            
            # if there is phase change, add phase change info to DB and regenerate output with new phase
            else:
                new_phase = phase_manager.getCurrPhase().getName()
                addMessage("PHASE", new_phase)
                print(f"conversation #{index} changed to {new_phase} phase")
                continue

            # user input from "user simulator"
            user_input = await agentResponse(index, getHistory())
            # print(f"User: {user_input}")
            addMessage("USER", user_input)

            # conversation finishing signal from user
            if user_input in ("<COMPLETE_CONVERSATION>", "quit"):
                break

        # save finished dialogue into csv file
        saveConversation(index, "./llm dialogues.csv")
        print(f"conversation #{index} saved...")

        # set current phase to start phase
        start_phase = phase_manager.getStartPhase().getName()
        phase_manager.setCurrPhase(start_phase)

        # reset DB for new chatbot
        reset()
        addMessage("PHASE", start_phase)

    return


# test with human input
async def manualTest(phase_manager: PhaseManager):
    while True:
        # make chatbot response
        response, changed = await executeChatbot(phase_manager, getHistory())
        
        # finish the dialogue if the next phase is FINISH
        if phase_manager.getCurrPhase().getName() == "FINISH":
            print("AI: " + response)
            addMessage("AI", response)
            break
        
        # if there is no phase change, use generated output
        if not changed:
            print("AI: " + response)
            addMessage("AI", response)
        
        # if there is phase change, add phase change info to DB and regenerate output with new phase
        else:
            addMessage("PHASE", phase_manager.getCurrPhase().getName())
            continue

        # user input from the human
        user_input = input("USER: ")
        if user_input == "quit":
            break
        else:
            addMessage("USER", user_input)


# dialogue evaluation
def eval():
    for index in range(1, 51):
        eval_result = autoEvaluation(index)

        file_exists = os.path.exists("./evaluation results.csv")

        with open(
            "./evaluation results.csv", mode="a", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(
                    [
                        "index",
                        "intent score",
                        "LLM score",
                        "intent score reason",
                        "LLM score reason",
                    ]
                )
            writer.writerow(
                [
                    index,
                    eval_result.score1,
                    eval_result.score2,
                    eval_result.reason1,
                    eval_result.reason2,
                ]
            )

        print(f"evaluation {index} clear...")


# emotion recognition test
async def emoRecogTest(phase_manager: PhaseManager):
    while True:
        # make chatbot response
        response, changed = await executeChatbot(phase_manager, getHistory())
        
        # if there is no phase change, use generated output
        if not changed:
            print("AI: " + response)
            addMessage("AI", response)

        # if there is phase change, print the new phase name and quit the conversation
        else:
            new_phase = phase_manager.getCurrPhase().getName()
            print(f"New Phase: {new_phase}")
            break

        # user input from the human
        user_input = input("USER: ")
        addMessage("USER", user_input)

        # conversation finishing signal from user
        if user_input == "quit":
            break

    return



# =================================================================================================================================================
# Execution Code
# =================================================================================================================================================


if __name__ == "__main__":
    # Set API key
    load_dotenv()

    # Check for test option
    parser = argparse.ArgumentParser()
    parser.add_argument("--autotest", action="store_true", help="for auto test")
    parser.add_argument("--mantest", action="store_true", help="for manual test")
    parser.add_argument("--eval", action="store_true", help="for evaluation")
    parser.add_argument("--recog", action="store_true", help="for recognition test")
    args = parser.parse_args()
    ATEST, MTEST, EVAL, RECOG = False, False, False, False
    if args.autotest:
        ATEST = True
    elif args.mantest:
        MTEST = True
    elif args.eval:
        EVAL = True
    elif args.recog:
        RECOG = True

    # execute main function
    if ATEST:
        data = getTestSettingData()
        phase_manager = saveTestSetting(data)
        asyncio.run(autoTest(phase_manager))
    elif MTEST:
        data = getTestSettingData()
        phase_manager = saveTestSetting(data)
        asyncio.run(manualTest(phase_manager))
    elif EVAL:
        eval()
    elif RECOG:
        data = getTestSettingData()
        phase_manager = saveTestSetting(data)
        asyncio.run(emoRecogTest(phase_manager))
    else:
        main()
