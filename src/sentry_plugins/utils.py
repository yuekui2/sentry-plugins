from __future__ import absolute_import


def get_secret_field_config(secret, help_text, include_prefix=False, **kwargs):
    has_saved_value = bool(secret)
    saved_text = 'Only enter a new value if you wish to update the existing one. '
    context = {
        'type': 'secret',
        'has_saved_value': has_saved_value,
        'prefix': (secret or '')[:4] if include_prefix else '',
        'required': not has_saved_value,
        'help': '%s%s' % ((saved_text if has_saved_value else ''), help_text)
    }
    context.update(kwargs)
    return context


def get_standard_data_forwarder_event(event):
    props = {
        'eventId': event.event_id,
        'transaction': event.get_tag('transaction') or '',
        'release': event.get_tag('sentry:release') or '',
        'environment': event.get_tag('environment') or '',
    }
    if 'sentry.interfaces.Http' in event.interfaces:
        http = event.interfaces['sentry.interfaces.Http']
        headers = http.headers
        if not isinstance(headers, dict):
            headers = dict(headers or ())

        props.update({
            'requestUrl': http.url,
            'requestMethod': http.method,
            'requestReferer': headers.get('Referer', ''),
        })
    if 'sentry.interfaces.Exception' in event.interfaces:
        exc = event.interfaces['sentry.interfaces.Exception'].values[0]
        props.update({
            'exceptionType': exc.type,
        })
    return props
