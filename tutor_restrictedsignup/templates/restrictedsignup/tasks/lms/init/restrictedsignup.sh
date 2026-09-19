echo "tutor-contrib-restrictedsignup: enabling instructor.legacy_instructor_dashboard waffle flag"
./manage.py lms shell -c "
from waffle.models import Flag
flag, _ = Flag.objects.get_or_create(name='instructor.legacy_instructor_dashboard')
flag.everyone = True
flag.save()
print('✓ Legacy dashboard enabled' if not created else '✓ Legacy dashboard flag created and enabled')
"
# instructor.legacy_instructor_dashboard set to: everyone=True