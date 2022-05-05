from prompt_toolkit.layout.containers import to_container


class ReferencedSplit:
    def __init__(self, split, children, *args, **kwargs) -> "None":
        self.container = split([], *args, **kwargs)
        self.children = children

    @property
    def children(self):
        return [to_container(x) for x in self._children]

    @children.setter
    def children(self, children):
        self._children = children
        self.container.children = self.children

    def __pt_container__(self) -> "Container":
        return self.container
