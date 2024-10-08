from difflib import SequenceMatcher
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
                if len(line) > 3:
                    patches.append(('-', line[3:]))
            elif line.startswith('+++'):
                if len(line) > 3:
                    patches.append(('+', line[3:]))
            else:
                patches.append((' ', line))
        print(patches)
        # split the patch into clusters
        clusters = self.find_change_clusters(patches)

        for cluster in clusters:
            # find the best match for the patch in the original file
            best_match = None
            best_score = -1
            for content in self.expand_cluster_content(patches, cluster):
                match_index, match_score = self.find_in_lines(lines, content)
                if match_score > best_score:
                    best_match = (match_index, content)
                    best_score = match_score
            
            if best_match is None:
                raise ValueError("Suitable patch location not found in the file")
            
            # add the patch to the result
            start_index, content = best_match
            lines = self.apply_patch(lines, content, start_index)

        # make sure all lines end with a newline
        lines = [line if line.endswith('\n') else line + '\n' for line in lines]

        return lines, "Patch applied successfully"

    def find_in_lines(self, lines, patch):
        non_plus = [p for p in patch if p[0] != '+']
        if len(non_plus) == 0:
            return -1, 0
        
        patch_text = '\n'.join(p[1].strip() for p in non_plus)
        best_match = -1
        best_ratio = 0
        
        for i in range(len(lines) - len(non_plus) + 1):
            window = '\n'.join(lines[i:i+len(non_plus)]).strip()
            ratio = SequenceMatcher(None, patch_text, window).ratio()
            if ratio > best_ratio and ratio >= 0.7:
                best_ratio = ratio
                best_match = i
        
        return best_match, best_ratio

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
        if current_cluster:
            clusters.append((cluster_start, cluster_end, current_cluster))
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


