import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.entry.models import SourcePreview


@csrf_exempt
def handle_pdf_generation(request):
    """
    AWS sends success/error response after pdf generation to this API.
    """
    data = json.loads(request.POST['event'])
    request_payload = data['requestPayload']
    response = data['responsePayload']
    try:
        preview = SourcePreview.objects.get(token=request_payload['token'])
    except SourcePreview.DoesNotExist:
        return JsonResponse({'message': 'Cannot find the preview'})

    if 'body' in response:
        preview.completed = True
        # preview.pdf_url = response['body']
        # https://stackoverflow.com/a/50804853/3218199
        preview.pdf = preview.token + '.pdf'
    else:
        preview.completed = False
        preview.reason = response['errorMessage']
    preview.save()
    return JsonResponse({'message': 'OK'})
