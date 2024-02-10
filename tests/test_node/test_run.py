from triotp import node, application

from . import sample_app


def test_node_run(test_data):
    node.run(
        apps=[
            application.app_spec(
                module=sample_app, start_arg=test_data, permanent=False
            )
        ]
    )

    assert test_data.count == 1
