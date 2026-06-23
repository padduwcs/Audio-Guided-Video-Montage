"""
Transaction Log & Undo/Redo/Audit for Review UI (Stage 7).

- Ghi lại mọi thao tác chỉnh sửa (transaction).
- Hỗ trợ undo/redo không giới hạn.
- Audit log thao tác (có thể export).
"""

import copy
import time

class TransactionLog:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.audit_log = []
        self.current_state = None

    def record_state(self, state, action, user="system"):
        # Lưu trạng thái mới vào undo stack, clear redo stack
        state_copy = copy.deepcopy(state)
        self.undo_stack.append(state_copy)
        self.redo_stack.clear()
        self.audit_log.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "user": user
        })
        self.current_state = state_copy

    def undo(self):
        if len(self.undo_stack) > 1:
            # Pop current state, push to redo
            self.redo_stack.append(self.undo_stack.pop())
            self.current_state = copy.deepcopy(self.undo_stack[-1])
            self.audit_log.append({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "action": "undo",
                "user": "system"
            })
            return copy.deepcopy(self.current_state)
        return None

    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(copy.deepcopy(state))
            self.current_state = copy.deepcopy(state)
            self.audit_log.append({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "action": "redo",
                "user": "system"
            })
            return copy.deepcopy(self.current_state)
        return None

    def get_audit_log(self):
        return list(self.audit_log)

    def reset(self, state):
        self.undo_stack = [copy.deepcopy(state)]
        self.redo_stack = []
        self.audit_log = []
        self.current_state = copy.deepcopy(state)

    def can_undo(self):
        return len(self.undo_stack) > 1

    def can_redo(self):
        return len(self.redo_stack) > 0