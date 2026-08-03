from django.conf import settings
from django.http import JsonResponse


def env_check(request):
    return JsonResponse({
        "SPARROW_TOKEN_SET": bool(settings.SPARROW_TOKEN),
        "SPARROW_SENDER_SET": bool(settings.SPARROW_SENDER),
        "DEBUG": settings.DEBUG,
        "SPARROW_SENDER": settings.SPARROW_SENDER,
        "TOKEN_PREFIX": settings.SPARROW_TOKEN[:8] + "..." if settings.SPARROW_TOKEN else None,
    })


from dotenv import load_dotenv
import os

load_dotenv()

print(os.getenv("SPARROW_TOKEN"))
print(os.getenv("SPARROW_SENDER"))