"""Desktop integration check; does not modify saved customer files."""
from browser_helpers import wait_canvas
import asyncio
import os
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1100})
  await page.goto(os.environ.get('MKP_TEST_URL','http://127.0.0.1:8510'),wait_until='networkidle')
  iframe=page.locator('iframe[src*="mkp_designer2d"]').first
  await iframe.wait_for();frame=await (await iframe.element_handle()).content_frame()
  frame=await wait_canvas(iframe,'args && args.mode==="walls"')
  await frame.get_by_role('button',name='Draw wall',exact=True).click()
  await frame.locator('#plan').scroll_into_view_if_needed()
  for x,y in ((2500,1000),(2500,2000)):
   point=await frame.evaluate('([x,y])=>{let p=svg.createSVGPoint();p.x=x;p.y=y;let q=p.matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y}}',[x,y])
   iframe_box=await iframe.bounding_box();await page.mouse.click(iframe_box['x']+point['x'],iframe_box['y']+point['y'])
  frame=await wait_canvas(iframe,'args.layout.walls.length===1')
  print('Two-click wall drawing passed')
  await page.get_by_role('button',name='Confirm room layout',exact=True).click()
  await page.get_by_role('button',name='Add custom worktop',exact=True).click()
  await page.get_by_label('Depth (mm)',exact=True).fill('1800')
  await page.get_by_role('button',name='Apply precise dimensions',exact=True).click()
  unit_iframe=page.locator('iframe[src*="mkp_designer2d"]').last
  await unit_iframe.wait_for();unit_frame=await (await unit_iframe.element_handle()).content_frame()
  unit_frame=await wait_canvas(unit_iframe,'args.units.length===1 && args.units[0].row["Depth (mm)"]===1800')
  await page.get_by_text('Worktop starting shape',exact=True).wait_for()
  # Streamlit selectboxes use listboxes, not native select elements.
  shape=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Worktop starting shape',exact=True))
  await shape.locator('[role="combobox"]').click()
  await shape.locator('[role="combobox"]').press('ArrowDown')
  await shape.locator('[role="combobox"]').press('Enter')
  await page.get_by_role('button',name='Load worktop starting shape',exact=True).click()
  iframe=page.locator('iframe[src*="mkp_designer2d"]').last
  await iframe.wait_for();frame=await (await iframe.element_handle()).content_frame()
  frame=await wait_canvas(iframe,'args.units.length===1 && args.units[0].polygons.length===2')
  assert await frame.locator('polygon.unit').count()==2
  print('Custom L worktop with an empty inner corner passed')
  await page.get_by_text('3D',exact=True).click()
  await page.get_by_text('Show room walls in preview',exact=True).click()
  await page.get_by_test_id('stPlotlyChart').wait_for()
  assert not await page.get_by_test_id('stException').count()
  print('3D worktop and room wall preview passed')
  await browser.close()

asyncio.run(main())
