..
    Regression: YAML ``- name:`` items inside an indented
    ``.. code-block:: yaml`` body were dispatched as bullets --
    nested-list dispatch fired before the directive handler.
    Found in Ansible porting guides.

* Conditionals - due to mitigation of security issue CVE-2023-5764
  in ansible-core 2.14.12, conditional expressions with embedded
  template blocks can fail when the embedded template consults
  untrusted data.

  .. code-block:: yaml

     - name: task with a module result (always untrusted by Ansible)
       shell: echo "hi mom"
       register: untrusted_result
