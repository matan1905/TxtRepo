from .base import DslInstruction


class EditSectionInstruction(DslInstruction):
    MAX_CONTEXT_SIZE = 5
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

        patches = []
        for line in patch_lines:
            if line.startswith('---'):
                patches.append(('-', line[3:]))
            elif line.startswith('+++'):
                patches.append(('+', line[3:]))
            else:
                patches.append((' ', line))

        # split the patch into clusters
        clusters = self.find_change_clusters(patches)

        start_index = -1
        for cluster in clusters:
            # find the best match for the patch in the original file
            for content in self.expand_cluster_content(patches, cluster):
                start_index = self.find_in_lines(lines, content)
                if start_index != -1:
                    break
            if start_index == -1:
                raise ValueError("Suitable patch location not found in the file")
            # add the patch to the result
            lines = self.apply_patch(lines, content, start_index)

        # make sure all lines end with a newline
        lines = [line if line.endswith('\n') else line + '\n' for line in lines]

        return lines, "Patch applied successfully"

    def find_in_lines(self, lines, patch):
        # if the whole patch is op '+' then we return -1
        if all(p[0] == '+' for p in patch):
            return -1
        for i in range(len(lines) - len(patch) + 1):
            if all(lines[i + j].strip() == p[1].strip() for j, p in enumerate(patch) if p[0] in (' ', '-')):
                return i
        return -1

    def apply_patch(self, lines, patch, start_index):
        result = lines[:start_index]
        i = start_index
        for op, line in patch:
            if op == ' ':
                result.append(line)
                i += 1
            elif op == '-':
                i += 1
            elif op == '+':
                result.append(line)
        result.extend(lines[i:])
        return result



    @classmethod
    def parse(cls, args):
        return cls()

    def find_change_clusters(self, patches):
        clusters = []
        current_cluster = []
        cluster_start = None
        cluster_end = None

        for i, (op, line) in enumerate(patches):
            if op in ('+', '-'):
                if not current_cluster:
                    cluster_start = i
                current_cluster.append((op, line))
                cluster_end = i
            elif current_cluster:
                clusters.append((cluster_start, cluster_end, current_cluster))
                current_cluster = []
                cluster_start = None
                cluster_end = None
        return clusters

    def expand_cluster_content(self, patches, cluster):
        cluster_start, cluster_end, cluster_content = cluster
        # keep returning the cluster while also expanding it from up, down and then up AND down
        for i in range(0, self.MAX_CONTEXT_SIZE + 1):
            for j in range(0, self.MAX_CONTEXT_SIZE + 1):
                if i == 0 and j == 0:
                    yield cluster_content
                    continue
                new_cluster_start = cluster_start - i
                new_cluster_end = cluster_end + j
                if new_cluster_start < 0 or new_cluster_end > len(patches):
                    continue
                new_cluster_content = patches[new_cluster_start:new_cluster_end]
                yield new_cluster_content


