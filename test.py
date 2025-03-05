from DB import initialize, addMessage, getHistory, reset

initialize()

addMessage("PHASE", "GREETING")
addMessage("USER", "Hello")
addMessage("AI", "Hello! It’s wonderful to hear from you. I’m here to support you in understanding and embracing your emotions and desires. Let’s begin by exploring how you’re feeling or what’s on your mind. You can share as much or as little as you’d like—this is a safe, supportive space. Once we’ve talked a bit, I’ll guide you to a small step, or micro-intervention, to help you focus on what’s important right now. Shall we start?")
addMessage("USER", "yes I am nervous")
addMessage("AI", "Thank you for sharing that with me. Feeling nervous can be challenging, but it’s completely okay to feel this way—it shows how much you care about what’s ahead. Could you tell me a little more about what might be causing your nervousness or how it’s making you feel in this moment? Understanding this together can help us figure out the best way to move forward.")
addMessage("USER", "I'm hot and my heart is bouncing...")
addMessage("AI", "It sounds like your nervousness is also having some physical effects on you—feeling hot and noticing your heart racing can be signs that your body is responding to this emotion. Thank you for sharing this with me; it’s important to listen to what your body is telling you. As we’ve explored both your emotions and how they’re affecting you physically, I’ll guide you to a small, focused step next—what we call a micro-intervention. This can help you connect with yourself more deeply. Let’s move into the next phase to explore this together.")

print(getHistory())
