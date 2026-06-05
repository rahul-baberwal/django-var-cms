import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from var_cms.registry import var_cms_site

def main():
    print("Exporting CMS documentation to static HTML...")
    
    # Create request factory and mock an authenticated request
    rf = RequestFactory()
    request = rf.get('/var-cms/about/')
    
    # Set default values for export in docs/index.html to the developer profile
    var_cms_site.site_url = "https://rahulbaberwal.com"
    var_cms_site.developer_name = "Rahul Baberwal"
    var_cms_site.developer_email = "im@rahulbaberwal.com"
    var_cms_site.developer_image = "https://github.com/rahul-baberwal.png"
    
    # Create or fetch a mock superuser to pass authorization checks
    User = django.apps.apps.get_model('auth', 'User')
    mock_user = User(username="Rahul Baberwal", email="im@rahulbaberwal.com", is_superuser=True)
    request.user = mock_user
    
    try:
        # Get the compiled HttpResponse from the CMS view
        response = var_cms_site.about_view(request)
        if response.status_code != 200:
            print(f"Error: View returned status code {response.status_code}")
            sys.exit(1)
            
        html_content = response.content.decode('utf-8')
        
        # Ensure the docs directory exists
        os.makedirs("docs", exist_ok=True)
        
        # 1. Copy the logo file to docs/var.png
        import shutil
        shutil.copy(os.path.join("var_cms", "static", "var_cms", "var.png"), os.path.join("docs", "var.png"))
        
        # 2. Favicon logo link fallback to the copied logo
        html_content = html_content.replace('href="/static/var_cms/var.png"', 'href="var.png"')
        
        # 3. Replace the default inline SVG with the custom img tag pointing to var.png for GitHub Pages
        import re
        html_content = re.sub(
            r'(<div class="brand-icon"[^>]*>)\s*<svg[^>]*>.*?</svg>\s*(</div>)',
            r'\1\n          <img src="var.png" style="width:100%; height:100%; object-fit:contain;" />\n        \2',
            html_content,
            flags=re.DOTALL
        )
        
        # 4. Redirect help page link to stay on the current static page
        html_content = html_content.replace('href="/var-cms/about/"', 'href="#"')
        
        # 5. Make sure the View Site link opens in a new tab (target="_blank")
        html_content = html_content.replace('title="View Site"', 'title="View Site" target="_blank"')
        
        # 6. Intercept and alert on other CMS links
        alert_msg = "This is a static HTML preview of the django-var-cms documentation. Database management and CMS actions are only active when running the Django server."
        
        # Replace main index / dashboard link
        html_content = html_content.replace('href="/var-cms/"', f'href="javascript:void(0)" onclick="alert(\'{alert_msg}\')"')
        
        # Replace logout link
        html_content = html_content.replace('href="/var-cms/logout/"', f'href="javascript:void(0)" onclick="alert(\'{alert_msg}\')"')
        
        # Replace django admin links
        html_content = html_content.replace('href="/admin/"', f'href="javascript:void(0)" onclick="alert(\'{alert_msg}\')"')
        
        # Replace any other /var-cms/app/model/ link in the sidebar or tables
        html_content = re.sub(
            r'href="/var-cms/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/"',
            f'href="javascript:void(0)" onclick="alert(\'{alert_msg}\')"',
            html_content
        )
        
        # Write compilation to docs/index.html
        with open(os.path.join("docs", "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("Success! Documentation compiled to docs/index.html")
        print("You can now enable GitHub Pages on the 'docs' folder of your repository.")
    except Exception as e:
        print(f"Failed to export documentation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
