import asyncio
import os
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1100})
  await page.goto(os.environ.get('MKP_TEST_URL','http://127.0.0.1:8515'),wait_until='networkidle')
  await page.get_by_text('Business libraries and workshop settings',exact=True).click()
  await page.get_by_text('Materials and fixtures library',exact=True).click()
  await page.get_by_role('button',name='Add illustrative starter products',exact=True).click()
  await page.get_by_role('button',name='Confirm room layout',exact=True).click()
  await page.get_by_text('Place library finishes, fixtures and appliances',exact=True).click()
  select=page.get_by_test_id('stSelectbox').filter(has_text='Placement library category')
  await select.locator('[role="combobox"]').click()
  await page.get_by_role('option',name='Tap',exact=True).click()
  await page.get_by_role('button',name='Place library product',exact=True).click()
  iframe=page.locator('iframe[src*="mkp_designer2d"]').last
  frame=await (await iframe.element_handle()).content_frame()
  await frame.wait_for_function('args.units.length===1 && args.units[0].row.Name.startsWith("Sample tap")')
  row=await frame.evaluate('args.units[0].row')
  assert row['Width (mm)']==180 and row['Height (mm)']==350
  assert '"catalogue_category": "Tap"' in row['Design details']
  assert not await page.get_by_test_id('stException').count()
  print('Starter catalogue, category selection and dimensional tap placement passed')
  await browser.close()

asyncio.run(main())
