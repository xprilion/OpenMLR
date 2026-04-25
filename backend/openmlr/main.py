"""OpenMLR CLI entry point (for future use)."""


def main():
    """Start the OpenMLR server."""
    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()
    uvicorn.run("openmlr.app:app", host="0.0.0.0", port=3000, reload=True)


if __name__ == "__main__":
    main()
