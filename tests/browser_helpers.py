"""Wait for validated canvas state across normal Streamlit iframe remounts."""
import asyncio
import time
from playwright.async_api import Error as PlaywrightError

async def wait_canvas(iframe,expression,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            handle=await iframe.element_handle(timeout=500)
            frame=await handle.content_frame() if handle else None
            if frame:
                await frame.wait_for_function(expression,timeout=500)
                return frame
        except PlaywrightError:
            pass
        await asyncio.sleep(.05)
    raise AssertionError('Canvas did not reach expected state: '+expression)
