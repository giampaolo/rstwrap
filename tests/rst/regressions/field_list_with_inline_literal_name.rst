..
    Regression: a field list whose field name is an inline literal
    (``:``p_offset``: segment file offset``) is valid RST -- docutils
    parses it as a field_list with an inline-literal field_name. Our
    ``_FIELD_LIST_RE`` excluded backticks from the field-name charset
    (to avoid matching ``:role:`text``` inline markup), which also
    excluded legitimate inline-literal field names. Encountered in the
    Linux kernel's ``Documentation/arch/arm64/memory-tagging-extension
    .rst``. The trailing ``:(?:\s|$)`` already disambiguates roles
    (which have no space after the closing colon), so the backtick
    exclusion is not needed.

Some prose paragraph before the field list.

:``p_type``: ``PT_AARCH64_MEMTAG_MTE``
:``p_flags``: 0
:``p_offset``: segment file offset
:``p_vaddr``: segment virtual address, same as the corresponding
  ``PT_LOAD`` segment
:``p_paddr``: 0

Trailing prose paragraph.
