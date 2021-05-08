# -*- coding: utf-8 -*-
import asyncio

from .app import App


def main():
    """Launch the application."""
    asyncio.run(App.launch())


if __name__ == "__main__":
    main()
