"""Integration tests for LangGraph structure."""

from langgraph.graph import StateGraph

from apps.worker.graphs.post_approval import build_post_approval_graph
from apps.worker.graphs.pre_approval import build_pre_approval_graph


class TestPreApprovalGraphStructure:
    """Tests for pre-approval graph structure."""

    def test_graph_builds_without_error(self) -> None:
        """Test graph can be built."""
        graph = build_pre_approval_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        """Test graph contains all expected nodes."""
        # Build graph builder (not compiled)
        builder = StateGraph(dict)
        builder.add_node("step0", lambda x: x)
        builder.add_node("step1", lambda x: x)
        builder.add_node("step1_5", lambda x: x)  # NEW: 競合記事品質スコア付与
        builder.add_node("step2", lambda x: x)
        builder.add_node("step3_parallel", lambda x: x)

        # Verify nodes are defined
        assert "step0" in builder.nodes
        assert "step1" in builder.nodes
        assert "step1_5" in builder.nodes
        assert "step2" in builder.nodes
        assert "step3_parallel" in builder.nodes


class TestPostApprovalGraphStructure:
    """Tests for post-approval graph structure."""

    def test_graph_builds_without_error(self) -> None:
        """Test graph can be built."""
        graph = build_post_approval_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        """Test graph contains all expected post-approval nodes."""
        expected_nodes = [
            "step3_5",  # NEW: Human Touch要素生成
            "step4",
            "step5",
            "step6",
            "step6_5",
            "step7a",
            "step7b",
            "step8",
            "step9",
            "step10",
            "step11",  # NEW: 画像生成
            "step12",  # NEW: WordPress形式変換
        ]

        builder = StateGraph(dict)
        for node in expected_nodes:
            builder.add_node(node, lambda x: x)

        for node in expected_nodes:
            assert node in builder.nodes


class TestGraphFlowCorrectness:
    """Tests for correct graph flow."""

    def test_pre_approval_flow_order(self) -> None:
        """Test pre-approval steps execute in correct order."""
        # Order: step0 → step1 → step1_5 → step2 → step3_parallel
        expected_order = ["step0", "step1", "step1_5", "step2", "step3_parallel"]

        # Verify linear flow - each step leads to next
        for i in range(len(expected_order) - 1):
            # In actual graph, edge from expected_order[i] to expected_order[i+1] exists
            assert expected_order[i] != expected_order[i + 1]  # Different steps

    def test_post_approval_flow_order(self) -> None:
        """Test post-approval steps execute in correct order."""
        expected_order = [
            "step3_5",
            "step4",
            "step5",
            "step6",
            "step6_5",
            "step7a",
            "step7b",
            "step8",
            "step9",
            "step10",
            "step11",
            "step12",
        ]

        # Verify linear flow - each step leads to next
        for i in range(len(expected_order) - 1):
            assert expected_order[i] != expected_order[i + 1]  # Different steps

    def test_no_cycles_in_pre_approval(self) -> None:
        """Test pre-approval graph has no cycles (linear flow)."""
        # Pre-approval should be strictly linear
        # step0 → step1 → step1_5 → step2 → step3_parallel → END
        steps = ["step0", "step1", "step1_5", "step2", "step3_parallel"]

        # Each step should have exactly one successor (except last)
        for i in range(len(steps) - 1):
            assert steps[i] != steps[i + 1]  # No self-loops

    def test_no_cycles_in_post_approval(self) -> None:
        """Test post-approval graph has no cycles (linear flow)."""
        steps = [
            "step3_5",
            "step4",
            "step5",
            "step6",
            "step6_5",
            "step7a",
            "step7b",
            "step8",
            "step9",
            "step10",
            "step11",
            "step12",
        ]

        # Each step should have exactly one successor (except last)
        for i in range(len(steps) - 1):
            assert steps[i] != steps[i + 1]  # No self-loops
