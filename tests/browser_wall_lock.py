import asyncio
import os
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1100})
  await page.goto(os.environ.get('MKP_TEST_URL','http://127.0.0.1:8512'),wait_until='networkidle')
  await page.get_by_role('button',name='Add wall',exact=True).click()
  await page.get_by_text('Wall added. Review the plan and confirm the room layout.',exact=True).wait_for()
  await page.get_by_text('Draw walls and edit wall measurements',exact=True).click()
  await page.get_by_role('button',name='Unlock selected wall',exact=True).wait_for()
  iframe=page.locator('iframe[src*="mkp_designer2d"]').first
  await iframe.wait_for()
  candidates=[f for f in page.frames if 'mkp_designer2d' in f.url]
  frame=candidates[0] if candidates else await page.wait_for_event('framenavigated',predicate=lambda f:'mkp_designer2d' in f.url)
  await frame.wait_for_function('args.layout.walls.length===1 && args.layout.walls[0].Locked===true')
  print('Measured Add wall creates a locked wall')
  async def move(start,end):
   await frame.locator('#plan').scroll_into_view_if_needed()
   box=await iframe.bounding_box()
   async def point(xy):
    return await frame.evaluate('([x,y])=>{let p=svg.createSVGPoint();p.x=x;p.y=y;let q=p.matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y}}',xy)
   a=await point(start);b=await point(end)
   await page.mouse.move(box['x']+a['x'],box['y']+a['y']);await page.mouse.down()
   await page.mouse.move(box['x']+b['x'],box['y']+b['y'],steps=10);await page.mouse.up()
  await move([1000,500],[1000,700])
  assert await frame.evaluate('args.layout.walls[0]["Start Y (mm)"]')==500
  print('Locked wall rejects movement')
  await page.get_by_role('button',name='Unlock selected wall',exact=True).click()
  for _ in range(40):
   try:
    handle=await iframe.element_handle();newframe=await handle.content_frame() if handle else None
    if newframe and await newframe.evaluate('typeof args!=="undefined" && args?.layout.walls[0]?.Locked===false'):
     frame=newframe;break
   except PlaywrightError:pass
   await page.wait_for_timeout(100)
  else:raise AssertionError('Unlocked wall canvas did not become ready')
  await frame.get_by_role('button',name='Move unlocked walls',exact=True).click()
  await move([1000,500],[1000,700])
  await frame.wait_for_function('Math.abs(args.layout.walls[0]["Start Y (mm)"]-700)<1')
  print('Unlocked wall moves as a whole')
  await move([1500,700],[1700,900])
  await frame.wait_for_function('Math.abs(args.layout.walls[0]["End X (mm)"]-1700)<1 && Math.abs(args.layout.walls[0]["End Y (mm)"]-900)<1')
  print('Unlocked endpoint movement passed')
  await page.get_by_role('button',name='Lock selected wall',exact=True).click()
  await page.get_by_role('button',name='Unlock selected wall',exact=True).wait_for()
  print('Re-lock passed')
  assert not await page.get_by_test_id('stException').count()
  await browser.close()

asyncio.run(main())
