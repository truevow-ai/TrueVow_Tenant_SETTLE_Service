"""
Extract case URLs directly from the current browser page
Uses JavaScript to extract all visible case links
"""
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# JavaScript code to extract all case URLs from the current page
EXTRACT_JS = """
() => {
    const urls = [];
    const baseUrl = 'https://www.casemine.com';
    const seen = new Set();
    
    // Method 1: Extract all judgment/case links
    document.querySelectorAll('a[href]').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        
        const fullUrl = href.startsWith('http') ? href : baseUrl + href;
        
        if (fullUrl.includes('casemine.com') && 
            (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/')) &&
            !fullUrl.includes('/search') && !fullUrl.includes('/login') && !fullUrl.includes('/signup') &&
            !fullUrl.includes('/home') && !fullUrl.includes('/about') &&
            !seen.has(fullUrl)) {
            seen.add(fullUrl);
            urls.push(fullUrl);
        }
    });
    
    // Method 2: Extract from result containers
    const containers = document.querySelectorAll('[class*="result"], [class*="case"], [class*="judgment"], article, [role="article"]');
    containers.forEach(container => {
        const links = container.querySelectorAll('a[href]');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;
            
            const fullUrl = href.startsWith('http') ? href : baseUrl + href;
            
            if (fullUrl.includes('casemine.com') && 
                (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/')) &&
                !seen.has(fullUrl)) {
                seen.add(fullUrl);
                urls.push(fullUrl);
            }
        });
    });
    
    return [...new Set(urls)];
}
"""

print("="*60)
print("Case URL Extraction from Browser Page")
print("="*60)
print("\nJavaScript code to run in browser console:")
print("-"*60)
print(EXTRACT_JS)
print("-"*60)
print("\nInstructions:")
print("1. Open browser console (F12)")
print("2. Paste the JavaScript code above")
print("3. Copy the resulting array of URLs")
print("4. Save to a text file (one URL per line)")
print("="*60)
