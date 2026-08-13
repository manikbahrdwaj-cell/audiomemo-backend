# Target file: tests/test_end_to_end_full_cart_and_checkout_flow_for_a_signed_in_user.py
# Generated execution model:
# - language: python
# - test_framework: pytest
# - playwright_api: sync_api
# Run completion: FULL
# Future page files:
# - pages/login_page.py
# - pages/listing_page.py
# - pages/cart_page.py
# - pages/content_page.py

import os
import pytest
import re
from playwright.sync_api import Page, expect

@pytest.fixture
def vtest_base_url() -> str:
    return 'https://www.saucedemo.com/'

@pytest.fixture
def test_data() -> dict:
    return {
        'username': 'standard_user',
        'password': os.environ.get('VTEST_DATA_PASSWORD', ""),
        'first_name': 'admin1',
        'zip_code': '1342',
    }

class LoginPage:
    PAGE_TYPE = 'login'
    LOCATOR_1 = '#user-name'
    LOCATOR_2 = '#password'
    LOCATOR_3 = '#login-button'

    def enter_standard_user_into_the_username_field(self, page: Page, test_data: dict) -> None:
        page.locator('#user-name').fill(test_data['username'])
        expect(page.locator('#user-name')).to_have_value(test_data['username'])

    def enter_secret_sauce_into_the_password_field(self, page: Page, test_data: dict) -> None:
        page.locator('#password').fill(test_data['password'])
        expect(page.locator('#password')).to_have_value(test_data['password'])

    def click_the_login_button(self, page: Page, test_data: dict) -> None:
        page.locator('#login-button').click()


class ListingPage:
    PAGE_TYPE = 'listing'
    LOCATOR_1 = '#add-to-cart-sauce-labs-backpack'
    LOCATOR_2 = 'a[data-test="shopping-cart-link"]'

    def click_the_add_to_cart_button_for_the_sauce_labs_backpack(self, page: Page, test_data: dict) -> None:
        page.locator('#add-to-cart-sauce-labs-backpack').click()

    def click_the_shopping_cart_icon(self, page: Page, test_data: dict) -> None:
        page.locator('a[data-test="shopping-cart-link"]').click()


class CartPage:
    PAGE_TYPE = 'cart'
    LOCATOR_1 = '#checkout'

    def click_the_checkout_button(self, page: Page, test_data: dict) -> None:
        page.locator('#checkout').click()


class ContentPage:
    PAGE_TYPE = 'content'
    LOCATOR_1 = '#first-name'
    LOCATOR_2 = '#last-name'
    LOCATOR_3 = '#postal-code'
    LOCATOR_4 = '#continue'

    def enter_admin1_into_the_first_name_field(self, page: Page, test_data: dict) -> None:
        page.locator('#first-name').fill(test_data['first_name'])
        expect(page.locator('#first-name')).to_have_value(test_data['first_name'])

    def enter_user1_into_the_last_name_field(self, page: Page, test_data: dict) -> None:
        page.locator('#last-name').fill(test_data['username'])
        expect(page.locator('#last-name')).to_have_value(test_data['username'])

    def enter_1342_into_the_zip_code_field(self, page: Page, test_data: dict) -> None:
        page.locator('#postal-code').fill(test_data['zip_code'])
        expect(page.locator('#postal-code')).to_have_value(test_data['zip_code'])

    def click_the_continue_button(self, page: Page, test_data: dict) -> None:
        page.locator('#continue').click()


def test_end_to_end_full_cart_and_checkout_flow_for_a_signed_in_user(page: Page, vtest_base_url: str, test_data: dict) -> None:
    page.goto(vtest_base_url)

    login_page = LoginPage()
    listing_page = ListingPage()
    cart_page = CartPage()
    content_page = ContentPage()

    login_page.enter_standard_user_into_the_username_field(page, test_data)
    login_page.enter_secret_sauce_into_the_password_field(page, test_data)
    login_page.click_the_login_button(page, test_data)
    listing_page.click_the_add_to_cart_button_for_the_sauce_labs_backpack(page, test_data)
    listing_page.click_the_shopping_cart_icon(page, test_data)
    cart_page.click_the_checkout_button(page, test_data)
    content_page.enter_admin1_into_the_first_name_field(page, test_data)
    content_page.enter_user1_into_the_last_name_field(page, test_data)
    content_page.enter_1342_into_the_zip_code_field(page, test_data)
    content_page.click_the_continue_button(page, test_data)

    assert 'checkout-step-two.html' in page.url
    expect(page.locator('body')).to_contain_text('Sauce Labs Backpack')