from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
import os
import tempfile
import logging
try:
    from backend.utils.ocr_helper import extract_exam_schedule
except ImportError:
    from utils.ocr_helper import extract_exam_schedule

logger = logging.getLogger(__name__)

class ParseExamScheduleView(views.APIView):
    """
    API endpoint to parse exam schedule from an uploaded image.
    """
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        image = request.FILES['image']
        
        # Save to temp file
        suffix = os.path.splitext(image.name)[1]
        if not suffix:
            suffix = '.png' # Default to png if no extension

        # Create a temp file
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in image.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
        except Exception as e:
            logger.error(f"Failed to save temp file: {e}")
            return Response({'error': 'Failed to process image file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        try:
            schedule = extract_exam_schedule(tmp_path)
            return Response({'schedule': schedule})
        except Exception as e:
            logger.error(f"Error parsing schedule: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
