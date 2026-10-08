"""Start with a persistent catalogue; the host supplies storage and secrets."""
from pathlib import Path
import os
import shutil


if __name__ == '__main__':
    if not os.environ.get('KITCHEN_APP_PASSWORD'):
        raise SystemExit('Configure KITCHEN_APP_PASSWORD in hosting secrets before starting.')
    catalogue = Path('/data/supplier_prices.json')
    if not catalogue.exists():
        shutil.copyfile('/app/supplier_prices.seed.json', catalogue)
    os.execvp('python', ['python', '-m', 'streamlit', 'run', 'app.py',
                        '--server.address=0.0.0.0', '--server.port=' + os.environ.get('PORT', '8501'),
                        '--server.headless=true', '--browser.gatherUsageStats=false'])
