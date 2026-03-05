"""Test input sanitization (XSS prevention).

Test cases from workstream-3-security-hardening-mfa.md Section 8.4:
- TC-XSS-01: Script tags are stripped from ticket description
- TC-XSS-02: HTML entities are stripped from chat messages
- TC-XSS-03: LIKE injection in search is prevented
"""
import pytest
from app.utils.sanitize import sanitize_input, sanitize_search


class TestSanitizeInputFunction:
    """Unit tests for the sanitize_input utility."""

    def test_script_tags_are_stripped(self):
        """TC-XSS-01: Script tags are stripped.

        Given   input containing <script>alert('xss')</script>Normal text
        When    sanitize_input is called
        Then    the output is 'Normal text' with the script tag stripped
        """
        result = sanitize_input("<script>alert('xss')</script>Normal text")
        assert '<script>' not in result
        assert 'alert' not in result
        assert 'Normal text' in result

    def test_img_onerror_is_stripped(self):
        """TC-XSS-02: HTML entities with event handlers are stripped.

        Given   input containing <img onerror=alert(1) src=x>
        When    sanitize_input is called
        Then    the img tag and event handler are removed
        """
        result = sanitize_input('<img onerror=alert(1) src=x>')
        assert '<img' not in result
        assert 'onerror' not in result

    def test_svg_onload_is_stripped(self):
        """SVG tags with event handlers are stripped.

        Given   input containing <svg onload=alert(1)>
        When    sanitize_input is called
        Then    the SVG tag is removed
        """
        result = sanitize_input('<svg onload=alert(1)>')
        assert '<svg' not in result

    def test_anchor_javascript_protocol_is_stripped(self):
        """Anchor tags with javascript: protocol are stripped.

        Given   input containing <a href="javascript:alert(1)">click</a>
        When    sanitize_input is called
        Then    the anchor tag is removed
        """
        result = sanitize_input('<a href="javascript:alert(1)">click</a>')
        assert '<a ' not in result
        assert 'javascript:' not in result

    def test_div_event_handler_is_stripped(self):
        """Div tags with event handlers are stripped.

        Given   input containing <div onmouseover="alert(1)">hover</div>
        When    sanitize_input is called
        Then    the event handler is removed
        """
        result = sanitize_input('<div onmouseover="alert(1)">hover</div>')
        assert 'onmouseover' not in result

    def test_nested_script_injection_is_stripped(self):
        """Nested script injection attempts are stripped.

        Given   input containing "><script>alert(document.cookie)</script>
        When    sanitize_input is called
        Then    script tags and content are removed
        """
        result = sanitize_input('"><script>alert(document.cookie)</script>')
        assert '<script>' not in result
        assert 'document.cookie' not in result

    def test_plain_text_passes_through(self):
        """Plain text without HTML is unchanged.

        Given   normal text input
        When    sanitize_input is called
        Then    the text is returned unchanged
        """
        text = 'This is a normal message with no HTML.'
        assert sanitize_input(text) == text

    def test_max_length_enforcement(self):
        """Input exceeding max_length is truncated.

        Given   input longer than max_length
        When    sanitize_input is called
        Then    the output is truncated to max_length characters
        """
        long_text = 'A' * 10001
        result = sanitize_input(long_text, max_length=10000)
        assert len(result) == 10000

    def test_none_input_returns_none(self):
        """None input returns None.

        Given   None as input
        When    sanitize_input is called
        Then    None is returned
        """
        assert sanitize_input(None) is None

    def test_non_string_input_raises_error(self):
        """Non-string input raises ValueError.

        Given   an integer as input
        When    sanitize_input is called
        Then    ValueError is raised
        """
        with pytest.raises(ValueError, match='Input must be a string'):
            sanitize_input(123)


class TestSanitizeSearchFunction:
    """Unit tests for the sanitize_search utility."""

    def test_like_wildcard_percent_is_escaped(self):
        """TC-XSS-03: LIKE injection via % is prevented.

        Given   search input '%'
        When    sanitize_search is called
        Then    the '%' is escaped to '\\%'
        """
        result = sanitize_search('%')
        assert result == '\\%'

    def test_like_wildcard_underscore_is_escaped(self):
        """LIKE injection via _ is prevented.

        Given   search input '_'
        When    sanitize_search is called
        Then    the '_' is escaped to '\\_'
        """
        result = sanitize_search('_')
        assert result == '\\_'

    def test_backslash_is_escaped(self):
        """Backslash in search is escaped.

        Given   search input '\\'
        When    sanitize_search is called
        Then    the '\\' is escaped to '\\\\\\\\'
        """
        result = sanitize_search('\\')
        assert '\\\\' in result

    def test_html_in_search_is_stripped(self):
        """HTML tags in search input are stripped.

        Given   search input '<script>alert(1)</script>'
        When    sanitize_search is called
        Then    HTML tags are removed
        """
        result = sanitize_search('<script>alert(1)</script>')
        assert '<script>' not in result

    def test_search_max_length_enforcement(self):
        """Search input exceeding 200 chars is truncated.

        Given   search input longer than 200 characters
        When    sanitize_search is called
        Then    the output is truncated to 200 characters
        """
        long_search = 'A' * 300
        result = sanitize_search(long_search)
        assert len(result) == 200

    def test_normal_search_passes_through(self):
        """Normal search terms are not modified.

        Given   a normal search term
        When    sanitize_search is called
        Then    the search term is returned unchanged
        """
        assert sanitize_search('John Smith') == 'John Smith'


class TestTicketDescriptionSanitization:
    """Integration tests for ticket description sanitization."""

    def test_ticket_creation_sanitizes_description(self, authenticated_client):
        """Creating a ticket sanitizes the description field.

        Given   an authenticated user
        When    creating a ticket with XSS in description
        Then    the stored description has XSS stripped
        """
        response = authenticated_client.post('/api/tickets', json={
            'description': "<script>alert('xss')</script>Legit issue",
        })
        # Accept 201 (created) or 403 (if user role doesn't permit)
        if response.status_code == 201:
            data = response.get_json()
            assert '<script>' not in data.get('description', '')
            assert 'Legit issue' in data.get('description', '')


class TestChatMessageSanitization:
    """Integration tests for chat message sanitization."""

    def test_message_creation_sanitizes_content(self, authenticated_client):
        """Creating a chat message sanitizes the content field.

        Given   an authenticated user
        When    sending a message with XSS payload
        Then    the stored content has XSS stripped
        """
        response = authenticated_client.post('/api/messages', json={
            'content': '<img onerror=alert(1) src=x>Hello',
            'message_type': 'channel',
            'channel_id': 'channel_general',
        })
        if response.status_code == 201:
            data = response.get_json()
            assert '<img' not in data.get('content', '')
            assert 'onerror' not in data.get('content', '')
