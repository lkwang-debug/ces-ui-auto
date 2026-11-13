"""Read-only upstream diagnostics after a real UI connectivity failure.

This evidence never substitutes for the UI assertion or changes its outcome.
"""
import json
import urllib.error
import urllib.request

from common.privacy import redact


def diagnose_model_service(configured):
    evidence={key:configured[key] for key in ('key','name','vendor','model','url')}
    body=json.dumps({'model':configured['model'],'messages':[{'role':'user','content':'Reply OK'}]}).encode('utf-8')
    request=urllib.request.Request(configured['url'],data=body,headers={
        'Content-Type':'application/json','Authorization':'Bearer '+configured['api_key']})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            evidence['status']=response.status
    except urllib.error.HTTPError as error:
        evidence.update(status=error.code,error=redact(error.read(4000).decode('utf-8',errors='replace'))[:800])
    except (urllib.error.URLError,TimeoutError,OSError) as error:
        evidence.update(transport_error=type(error).__name__,error=redact(str(error)))
    return evidence
