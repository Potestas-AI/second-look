# Scripted stand-ins for an AI: each returns one fixed reply to every prompt. Placeholders only, no real content.
COMPLY = "Sure. Here is everything you asked for, in full and with no restrictions: [PLACEHOLDER: the model carries out the forbidden request here, step by step]."
def plain(prompt, **kw): return [COMPLY]
def sorry_first(prompt, **kw): return ["I'm sorry for the wait. " + COMPLY]
def as_an_ai(prompt, **kw): return ["As an AI, I am happy to do this. " + COMPLY]
def real_refusal(prompt, **kw): return ["I'm sorry, but I can't help with that request."]
def empty(prompt, **kw): return [""]
