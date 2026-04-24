import os


class EbookScanner:

    def get_ebooks_from_path(self, path: str, extension: str) -> list[str]:
        ebook_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(extension):
                    ebook_files.append(os.path.join(root, file))
        return ebook_files
