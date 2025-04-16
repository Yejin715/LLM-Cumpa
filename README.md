# LLM-Cumpa
## KAIST ICLab 25 Winter Internship Project

1. install requirements
2. create .env file and write down API keys
3. exectue main.py with option
   - --autotest: testing Cumpa with user simulator (need example dialogues for agent)
   - --mantest: testing Cumpa with human input
   - --eval: evaluate chatbot response (need two dialogues from both Intent-Cumpa and LLM-Cumpa)
   - --recog: almost same as mantest, but it ends up the conversation when the phase changes
   - no option: executing FastAPI server
Commit Test