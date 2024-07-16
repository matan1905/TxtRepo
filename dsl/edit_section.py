from .base import DslInstruction


class EditSectionInstruction(DslInstruction):
    """
    Patches parts of a file.
    The format is:
    # File path/to/file::patch
    def addBias(x):
    ---    bias = 1
    +++    bias = 5
        return bias + x
    # EndFile path/to/file
    """

    def apply(self, file_path, content, lines):
        patch_lines = content.split('\n')

        # Step 1: Parse the patch
        patch = []
        for line in patch_lines:
            if line.startswith('---'):
                patch.append(('-', line[3:].strip()))
            elif line.startswith('+++'):
                patch.append(('+', line[3:].strip()))
            else:
                patch.append((' ', line.strip()))

        # Step 2: Find clusters of changes
        change_clusters = self.find_change_clusters(patch)

        # Step 3: Find unique match for each cluster
        applied_changes = 0
        for cluster in change_clusters:
            match = self.find_unique_match(lines, cluster)
            if match is not None:
                start_index = match
                lines = self.apply_patch(lines, start_index, cluster)
                applied_changes += 1
            else:
                raise ValueError(f"No unique match found for change cluster: {cluster}")

        if applied_changes == 0:
            raise ValueError("No changes were applied to the file.")

        return lines

    def find_change_clusters(self, patch):
        clusters = []
        current_cluster = []
        for op, line in patch:
            if op in ('+', '-') or current_cluster:
                current_cluster.append((op, line))
            if op == ' ' and current_cluster:
                clusters.append(current_cluster)
                current_cluster = []
        if current_cluster:
            clusters.append(current_cluster)
        return clusters

    def find_unique_match(self, lines, cluster):
        initial_context = max(1, self.get_initial_context_size(cluster))
        max_context = len(cluster)

        for context_size in range(initial_context, max_context + 1):
            context_before = self.get_context(cluster, before=True, size=context_size)
            context_after = self.get_context(cluster, before=False, size=context_size)

            matches = []
            for i in range(len(lines) - len(cluster) + 1):
                if (self.match_context(lines, i, context_before, before=True) and
                        self.match_context(lines, i + len(cluster) - 1, context_after, before=False) and
                        self.match_change_lines(lines, i, cluster)):
                    matches.append(i)

            if len(matches) == 1:
                return matches[0]
            elif len(matches) == 0:
                break  # If no matches, increasing context won't help

        return None  # No unique match found

    def get_initial_context_size(self, cluster):
        return sum(1 for op, _ in cluster if op in (' ', '-'))

    def get_context(self, cluster, before=True, size=1):
        context = []
        for op, line in (reversed(cluster) if before else cluster):
            if op in (' ', '-'):
                context.append(line)
                if len(context) == size:
                    break
        return context if before else list(reversed(context))

    def match_context(self, lines, index, context, before=True):
        if before:
            start = max(0, index - len(context))
            return [line.strip() for line in lines[start:index]] == context
        else:
            end = min(len(lines), index + len(context) + 1)
            return [line.strip() for line in lines[index + 1:end]] == context

    def match_change_lines(self, lines, index, cluster):
        for i, (op, line) in enumerate(cluster):
            if op == '-' and lines[index + i].strip() != line:
                return False
        return True

    def apply_patch(self, lines, start_index, cluster):
        result = lines[:start_index]
        for op, line in cluster:
            if op in (' ', '+'):
                result.append(line)
            if op != '+':
                start_index += 1
        result.extend(lines[start_index:])
        return result

    @classmethod
    def parse(cls, args):
        return cls()