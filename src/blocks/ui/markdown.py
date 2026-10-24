from ._kit import block


def markdown(text):
    return block("markdown", text=str(text))
