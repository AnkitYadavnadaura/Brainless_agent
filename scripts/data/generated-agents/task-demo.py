import json
DEFINITION = {'name': 'Web worker', 'role': 'BrowserAgent', 'objective': 'Visit website', 'task': 'Visit website', 'permissions': ['browser.navigate', 'screen.read'], 'tools': ['browser.navigate'], 'subscriptions': [], 'context': {}, 'resource_limits': {}, 'allowed_applications': [], 'allowed_directories': [], 'risk_policy': 'medium'}
print(json.dumps(DEFINITION))
