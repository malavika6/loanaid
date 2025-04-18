from django.test import TestCase
from .utils import get_sidebar_menu

class SidebarMenuTests(TestCase):
    def test_admin_menu(self):
        menu = get_sidebar_menu('admin')
        expected_menu = [
            {'name': 'Dashboard', 'url': '/'},
            {'name': 'Manage Franchises', 'url': '/list_franchise'},
            {'name': 'Manage Staff', 'url': '/list_staff'},
            {'name': 'Add Loan', 'url': '/add-loan'},
        ]
        self.assertEqual(menu, expected_menu)

    def test_franchise_menu(self):
        menu = get_sidebar_menu('franchise')
        expected_menu = [
            {'name': 'Dashboard', 'url': '/franchise_dashboard'},
            {'name': 'My Loans', 'url': '/loan-page'},
            {'name': 'Profile', 'url': '/profile'},
        ]
        self.assertEqual(menu, expected_menu)

    def test_staff_menu(self):
        menu = get_sidebar_menu('staff')
        expected_menu = [
            {'name': 'Dashboard', 'url': '/dashboard'},
            {'name': 'Assignments', 'url': '/staff_assignments'},
            {'name': 'Profile', 'url': '/profile'},
        ]
        self.assertEqual(menu, expected_menu)

    def test_executive_menu(self):
        menu = get_sidebar_menu('executive')
        expected_menu = [
            {'name': 'Dashboard', 'url': '/index/executive'},
            {'name': 'Profile', 'url': '/profile'},
        ]
        self.assertEqual(menu, expected_menu)

    def test_invalid_user_type(self):
        menu = get_sidebar_menu('invalid')
        self.assertEqual(menu, [])
