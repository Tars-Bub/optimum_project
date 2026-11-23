OPTIMUM - MOBILE VIEW UPDATE
============================
Your original code is kept. app.css and every other template are untouched.

NEW files (copy into your project, same folders):
  static/css/mobile.css
  static/js/mobile.js

CHANGED files (only lines marked "mobile" were added):
  templates/base.html       -> 1 <link> in <head>, 1 <script> before </body>
  templates/auth_base.html  -> 1 <link> in <head>

If your base.html is newer than this copy, do NOT overwrite it - just add the lines below.

In base.html, directly after the app.css <link> line:
  <link rel="stylesheet" href="{% static 'css/mobile.css' %}"><!-- mobile -->
and just before </body>:
  <script src="{% static 'js/mobile.js' %}" defer></script><!-- mobile -->

In auth_base.html, directly after the app.css <link> line:
  <link rel="stylesheet" href="{% static 'css/mobile.css' %}"><!-- mobile -->

To go back to the original look: delete those marked lines (or the two new files).
On Render / production run: python manage.py collectstatic --noinput
