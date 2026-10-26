"""Upload a real annotated PDF, convert reviewed measurements, and place a cabinet."""
import asyncio
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from playwright.async_api import async_playwright
from browser_helpers import wait_canvas

async def main():
 pdf=BytesIO();doc=canvas.Canvas(pdf)
 for i,text in enumerate(['Room length 4000 mm','Room depth 3000 mm','Door width 2800 mm','Door offset 600 mm','Door height 2100 mm','Window width 1000 mm','Window height 600 mm']):doc.drawString(60,780-i*35,text)
 doc.save()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1100})
  await page.goto(os.environ.get('MKP_TEST_URL','http://127.0.0.1:8520'),wait_until='networkidle')
  await page.get_by_text('Read a sketch, plan or PDF',exact=True).click()
  await page.locator('input[type=file]').last.set_input_files({'name':'test-room.pdf','mimeType':'application/pdf','buffer':pdf.getvalue()})
  await page.get_by_role('heading',name='Build an editable room from this plan',exact=True).wait_for()
  await page.get_by_label('Plan room length (mm)',exact=True).fill('4000')
  await page.get_by_label('Plan room length (mm)',exact=True).press('Enter')
  await page.get_by_label('Plan room depth (mm)',exact=True).fill('3000')
  await page.get_by_label('Plan room depth (mm)',exact=True).press('Enter')
  await page.get_by_label('Plan room height (mm)',exact=True).fill('2400')
  await page.get_by_label('Plan room height (mm)',exact=True).press('Enter')
  await page.get_by_label('Plan opening width (mm)',exact=True).fill('2800')
  await page.get_by_label('Plan opening width (mm)',exact=True).press('Enter')
  await page.get_by_label('Plan opening offset (mm)',exact=True).fill('600')
  await page.get_by_label('Plan opening offset (mm)',exact=True).press('Enter')
  await page.get_by_label('Plan opening height (mm)',exact=True).fill('2100')
  await page.get_by_label('Plan opening height (mm)',exact=True).press('Enter')
  await page.get_by_role('button',name='Stage opening from plan',exact=True).click()
  await page.get_by_text('Opening staged. Review its row below.',exact=True).wait_for()
  await page.get_by_text('I checked the room dimensions, opening positions, heights and sill levels against the original',exact=True).click()
  await page.get_by_role('button',name='Use reviewed plan and freeze room',exact=True).click()
  await page.get_by_text('Room structure frozen — walls, doors and windows stay fixed while you place cabinets.',exact=True).wait_for()
  await page.get_by_role('heading',name='Interactive 2D floor plan',exact=True).wait_for()
  iframe=page.locator('iframe[src*="mkp_designer2d"]').last
  frame=await wait_canvas(iframe,'args.mode!=="walls" && args.layout.length===4000 && args.layout.width===3000 && args.layout.openings.length===1')
  assert await frame.evaluate('args.layout.openings[0]["Width (mm)"]===2800 && args.layout.openings[0]["Offset (mm)"]===600')
  await frame.get_by_role('button',name='Add Single door base',exact=True).click()
  frame=await wait_canvas(iframe,'args.units.length===1')
  await iframe.scroll_into_view_if_needed()
  await page.screenshot(path='/tmp/mkp-plan-cad-workspace.png')
  assert not await page.get_by_label('Room length — x (mm)',exact=True).count()
  await page.get_by_role('button',name='Approve and lock layout',exact=True).wait_for()
  reference=page.get_by_text('Active plan reference — test-room.pdf',exact=True).last
  await reference.click()
  await page.get_by_text('Room length 4000 mm',exact=False).last.wait_for()
  assert await page.get_by_role('button',name='Download active room and plan reference',exact=True).last.is_enabled()
  assert not await page.get_by_test_id('stException').count()
  print('Automatic local reading → reviewed frozen room → editable cabinets → retained plan reference passed')
  await browser.close()

asyncio.run(main())
