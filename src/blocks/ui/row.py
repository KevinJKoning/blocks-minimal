from ._kit import block


def row(*blocks, title=None):
    """Blocks side by side, to compare (on a narrow page they wrap). The children are in the
    row's "blocks" field, where the page looks for blocks inside blocks."""
    if not all(isinstance(b, dict) and "type" in b for b in blocks):
        raise ValueError("ui.row takes blocks, like ui.row(ui.map(...), ui.map(...))")
    return block("row", title=title, blocks=list(blocks))
