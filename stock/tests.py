from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from catalog.models import Category, Product
class StockProductInputTests(TestCase):
    def test(self):
        U=get_user_model(); u=U.objects.create_user('a',password='x'); u.profile.status='active'; u.profile.save()
        c=Category.objects.create(name='C'); p=Product.objects.create(code='PAP-1',name='Paper',category=c)
        cl=Client(); cl.force_login(u)
        r=cl.get('/stock/?tab=incoming'); self.assertContains(r,'<datalist'); self.assertContains(r,'PAP-1 \u2014 Paper')
        r=cl.post('/stock/',{'form':'incoming','product':'pap-1','quantity':5}); self.assertEqual(r.status_code,302)
        r=cl.post('/stock/',{'form':'incoming','product':'PAP-1 \u2014 Paper','quantity':5}); self.assertEqual(r.status_code,302)
        p.refresh_from_db(); self.assertEqual(p.quantity,10)
        r=cl.post('/stock/',{'form':'adjust','product':'Paper','counted':3,'reason':'count'}); self.assertEqual(r.status_code,302)
        p.refresh_from_db(); self.assertEqual(p.quantity,3)
        r=cl.post('/stock/',{'form':'incoming','product':'zzz','quantity':5}); self.assertContains(r,'No active item')
