"""Bounded message context, shared by gateway integration and local inference."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from html.parser import HTMLParser


class PlainEmail(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.blocked = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'template'): self.blocked += 1
        if not self.blocked and tag in ('p','br','div','li','tr'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'template'): self.blocked = max(0,self.blocked-1)
    def handle_data(self, data):
        if not self.blocked: self.parts.append(data)


class DisplayedLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(default='', max_length=500)
    href: str = Field(max_length=2048)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=10000)
    message_type: Literal['sms','email'] = 'sms'
    text_format: Literal['plain','html'] = 'plain'
    subject: str = Field(default='', max_length=500)
    claimed_sender: str = Field(default='', max_length=320)
    reply_to: str = Field(default='', max_length=320)
    displayed_links: list[DisplayedLink] = Field(default_factory=list, max_length=50)
    optional_analysis: bool = False

    @field_validator('text','subject','claimed_sender','reply_to')
    @classmethod
    def no_nul(cls,v):
        if '\x00' in v: raise ValueError('NUL bytes are not supported')
        return v

    def canonical_text(self):
        body=self.text
        if self.text_format=='html':
            parser=PlainEmail();parser.feed(body);parser.close()
            body=''.join(parser.parts)
        return (self.subject+'\n\n'+body) if self.message_type=='email' and self.subject else body

    @model_validator(mode='after')
    def valid_content(self):
        if self.message_type=='sms' and (self.text_format!='plain' or self.subject or self.claimed_sender or self.reply_to or self.displayed_links):
            raise ValueError('Email context requires message_type=email')
        canonical=self.canonical_text()
        if not canonical.strip() or len(canonical)>10000:
            raise ValueError('Assessed subject and body must contain 1–10000 Unicode characters; shorten explicitly, never silently truncated')
        return self
