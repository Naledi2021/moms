"""Select a locked wall on the plan, correct its position, undo and inspect desktop styling."""
import asyncio
import os
from playwright.async_api import async_playwright, Error as PlaywrightError

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1100})
  await page.goto(os.environ.get('MKP_TEST_URL','http://127.0.0.1:8517'),wait_until='networkidle')
  await page.get_by_role('button',name='Add wall',exact=True).click()
  await page.get_by_role('button',name='Unlock selected wall',exact=True).wait_for()
  # Add another separate wall and choose it by clicking the floor plan.
  await page.get_by_label('Wall start Y (mm)',exact=True).fill('1500')
  await page.get_by_role('button',name='Add wall',exact=True).click()
  print('Two walls added',flush=True)
  iframe=page.locator('iframe[src*="mkp_designer2d"]').first
  await iframe.wait_for();frame=await (await iframe.element_handle()).content_frame()
  await frame.wait_for_function('args?.layout.walls.length===2')
  print('Wall editor open:',await page.get_by_text('Draw walls and edit wall measurements',exact=True).evaluate('el=>el.closest("details").open'),flush=True)
  await frame.locator('#plan').scroll_into_view_if_needed()
  point=await frame.evaluate('()=>{let p=svg.createSVGPoint();p.x=1000;p.y=1500;let q=p.matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y}}')
  box=await iframe.bounding_box()
  await page.mouse.click(box['x']+point['x'],box['y']+point['y'])
  print('Wall clicked',flush=True)
  for _ in range(60):
   try:
    frame=await (await iframe.element_handle()).content_frame()
    await frame.wait_for_function('args.selected===1',timeout=500);break
   except PlaywrightError:pass
  else:raise AssertionError('Wall selection did not update')
  await page.get_by_label('Position Y (mm)',exact=True).wait_for()
  await page.wait_for_function('document.querySelectorAll("input").length>0')
  await page.get_by_label('Position Y (mm)',exact=True).fill('1800')
  await page.get_by_role('button',name='Apply position and lock wall',exact=True).click()
  print('Correction submitted',flush=True)
  async def current_frame(expected_y):
   for _ in range(60):
    try:
     f=await (await iframe.element_handle()).content_frame()
     await f.wait_for_function('(y)=>args?.layout.walls.length===2 && args.layout.walls[1]["Start Y (mm)"]===y',arg=expected_y,timeout=500)
     return f
    except PlaywrightError:pass
   raise AssertionError('Corrected wall did not reach the plan')
  frame=await current_frame(1800)
  assert await frame.evaluate('args.layout.walls[0]["Start Y (mm)"]===500 && args.layout.walls[1].Locked===true')
  await page.get_by_role('button',name='Undo last wall change',exact=True).click()
  frame=await current_frame(1500)
  assert not await page.get_by_test_id('stException').count()
  assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  await page.get_by_text('Draw walls and edit wall measurements',exact=True).scroll_into_view_if_needed()
  await page.screenshot(path='/tmp/mkp-wall-editor-final.png',full_page=False)
  await page.get_by_role('heading',name='Kitchen Design Studio',exact=True).scroll_into_view_if_needed()
  await page.screenshot(path='/tmp/mkp-professional-studio.png',full_page=False)
  print('Plan selection, locked-wall correction, re-lock, undo and desktop layout passed')
  await browser.close()

asyncio.run(main())
