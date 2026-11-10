web: gunicorn config.wsgi --timeout 120 --log-file -
postdeploy: python manage.py migrate --noinput
