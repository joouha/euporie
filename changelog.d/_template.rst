{% set title = "v" ~ versiondata.version ~ " (" ~ versiondata.date ~ ")" %}
{% set title_underline = "*" * title|length %}
{{ title_underline }}
{{ title }}
{{ title_underline }}

{% for category, val in definitions.items() if category in sections[""] %}
{{ val['name'] }}
{{ "=" * val['name']|length }}

{% for text, values in sections[""][category].items() %}
- {{ text }}
{% endfor %}

{% endfor %}
----
