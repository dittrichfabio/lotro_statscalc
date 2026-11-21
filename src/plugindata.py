import re

class PluginDataParseError(ValueError):
    pass

_NAME_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_NUMBER_RE = re.compile(r'[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?|0[xX][0-9a-fA-F]+')

_ESCAPES = {
    'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r',
    't': '\t', 'v': '\v', '\\': '\\', '"': '"', "'": "'",
}


def load_plugindata(path):
    with open(path, 'r', encoding='utf-8') as f:
        return parse_plugindata(f.read())


def parse_plugindata(text):
    """Parse a .plugindata file (a `return <lua table literal>` document)."""
    parser = _Parser(text)
    result = parser.parse_document()
    parser.skip_ws()
    if parser.pos != len(parser.text):
        raise PluginDataParseError(f"Trailing data at offset {parser.pos}")
    return result


class _Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def skip_ws(self):
        text, pos, n = self.text, self.pos, len(self.text)
        while pos < n and text[pos] in ' \t\r\n':
            pos += 1
        self.pos = pos

    def peek(self):
        if self.pos < len(self.text):
            return self.text[self.pos]
        return ''

    def error(self, message):
        return PluginDataParseError(f"{message} at offset {self.pos}")

    def expect(self, char):
        self.skip_ws()
        if self.peek() != char:
            raise self.error(f"Expected '{char}'")
        self.pos += 1

    def parse_document(self):
        self.skip_ws()
        if self.text.startswith('return', self.pos):
            boundary = self.pos + len('return')
            if boundary >= len(self.text) or not (self.text[boundary].isalnum() or self.text[boundary] == '_'):
                self.pos = boundary
        return self.parse_value()

    def parse_value(self):
        self.skip_ws()
        c = self.peek()
        if c == '{':
            return self.parse_table()
        if c == '"' or c == "'":
            return self.parse_string()
        m = _NUMBER_RE.match(self.text, self.pos)
        if m:
            self.pos = m.end()
            token = m.group(0)
            if token.lower().startswith(('0x', '+0x', '-0x')):
                return int(token, 16)
            try:
                return int(token)
            except ValueError:
                return float(token)
        m = _NAME_RE.match(self.text, self.pos)
        if m:
            word = m.group(0)
            if word == 'true':
                self.pos = m.end()
                return True
            if word == 'false':
                self.pos = m.end()
                return False
            if word == 'nil':
                self.pos = m.end()
                return None
        raise self.error("Unexpected character")

    def parse_string(self):
        quote = self.text[self.pos]
        self.pos += 1
        out = []
        text, n = self.text, len(self.text)
        while self.pos < n:
            c = text[self.pos]
            if c == quote:
                self.pos += 1
                return ''.join(out)
            if c == '\\':
                self.pos += 1
                if self.pos >= n:
                    break
                e = text[self.pos]
                if e.isdigit():
                    digits = e
                    self.pos += 1
                    while self.pos < n and len(digits) < 3 and text[self.pos].isdigit():
                        digits += text[self.pos]
                        self.pos += 1
                    out.append(chr(int(digits)))
                    continue
                out.append(_ESCAPES.get(e, e))
                self.pos += 1
            else:
                out.append(c)
                self.pos += 1
        raise self.error("Unterminated string")

    def parse_table(self):
        self.expect('{')
        fields = {}
        array_index = 1
        while True:
            self.skip_ws()
            if self.peek() == '}':
                self.pos += 1
                break
            if self.peek() == '[':
                self.pos += 1
                key = self.parse_value()
                self.expect(']')
                self.expect('=')
                value = self.parse_value()
            elif self.peek() in '"\'':
                # ["Key"] = value is handled by the '[' branch; a bare quoted
                # string here is a positional (array) element.
                key = array_index
                array_index += 1
                value = self.parse_value()
            else:
                m = _NAME_RE.match(self.text, self.pos)
                if m:
                    probe = m.end()
                    while probe < len(self.text) and self.text[probe] in ' \t\r\n':
                        probe += 1
                    if probe < len(self.text) and self.text[probe] == '=':
                        key = m.group(0)
                        self.pos = probe + 1
                        value = self.parse_value()
                    else:
                        key = array_index
                        array_index += 1
                        value = self.parse_value()
                else:
                    key = array_index
                    array_index += 1
                    value = self.parse_value()
            fields[self._normalize_key(key)] = value
            self.skip_ws()
            if self.peek() in ',;':
                self.pos += 1
        if fields and all(isinstance(k, int) for k in fields):
            keys = sorted(fields)
            if keys == list(range(1, len(keys) + 1)):
                return [fields[k] for k in keys]
        return fields

    @staticmethod
    def _normalize_key(key):
        if isinstance(key, float) and key.is_integer():
            return int(key)
        return key
