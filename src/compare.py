import argparse
import tokenize
from tokenize import NAME, STRING, NUMBER, COMMENT
import unicodedata
import re
from collections import Counter


class ArgParser:
    """
    Обработчик аргументов командной строки

    input_file: файл с текстами для сравнения

    output_file: файл для вывода результата сравнения

    -d - опциональный аргумент, при значении True пропускаются комментарии и docstrings
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Parser for text comparator")
        self.parser.add_argument(
            "input_file", type=str, help="Input name of the original file"
        )
        self.parser.add_argument(
            "output_file", type=str, help="Input name of the edited file"
        )
        self.parser.add_argument(
            '-d', '-doc_com', type=str,
            help="Skip docstrings and comments for comparison"
        )
        self.parameters = self.parser.parse_args()


class Comparator:
    """
    В конструкторе инициализируются параметры результата,

    переменная для учета/пропуска комментариев и docstrings,

    словари с категориями контента
    """

    def __init__(self, *, skip_docs_and_comments=False):
        self._doc_com = not skip_docs_and_comments
        self._source_content = {
            "STRINGS": [],
            "DOCSTRINGS": [],
            "NUMBERS": [],
            "COMMENTS": [],
            "WORDS": [],
            "SHORT_WORDS": []
        }
        self._edited_content = {
            "STRINGS": [],
            "DOCSTRINGS": [],
            "NUMBERS": [],
            "COMMENTS": [],
            "WORDS": [],
            "SHORT_WORDS": []
        }
        self._result = -1

    def _file_process(self, *, filename: "files to compare", buf: dict[str]) -> None:

        """Метод для обработки файлов перед сравнением"""

        with open(filename, 'rb') as file:
            self._make_grouped_tokens(file, buf)

    def _make_grouped_tokens(self, file_obj: "opened file", buf: dict[str]) -> None:

        """Метод для разбиения текста на токены и добавления обработанного текста в словари категорий"""

        tokens = tokenize.tokenize(file_obj.readline)
        numbers_str = str()
        short_words_str = str()

        try:
            for token_type, token_val, _, _, _ in tokens:

                processed_string = str()
                if token_type == NAME:
                    buf["WORDS"].append(self.text_processing(token_val))

                elif token_type == COMMENT:
                    if not self._doc_com:
                        continue
                    com_string = str()
                    token_val_ = self.text_processing(token_val).lstrip('#')
                    if len(token_val_) <= 2:
                        short_words_str += token_val_
                    else:
                        for char in token_val_:
                            if 1072 <= ord(char) <= 1103 or 97 <= ord(char) <= 122:
                                com_string += char
                        buf["COMMENTS"].append(com_string)

                elif token_type == STRING:
                    if re.search(r'"""[\s\S]*?"""', token_val) and not self._doc_com:
                        continue
                    token_val_ = self.text_processing(token_val)
                    if re.search(r'"""[\s\S]*?"""', token_val_):
                        doc_string = str()
                        for char in token_val_:
                            if 1072 <= ord(char) <= 1103 or 97 <= ord(char) <= 122:
                                doc_string += char
                        buf["DOCSTRINGS"].append(doc_string)
                        continue
                    if re.search(r'"[\s\S]*?"', token_val_):
                        token_val_ = token_val_.strip('\"')
                        for char in token_val_:
                            if 1072 <= ord(char) <= 1103 or 97 <= ord(char) <= 122:
                                processed_string += char
                    elif re.search(r"'[\s\S]*?'", token_val_):
                        token_val_ = token_val_.strip('\'')
                        for char in token_val_:
                            if 1072 <= ord(char) <= 1103 or 97 <= ord(char) <= 122:
                                processed_string += char
                    if len(processed_string) <= 1:
                        short_words_str += processed_string
                        continue
                    buf["STRINGS"].append(processed_string)

                elif token_type == NUMBER:
                    numbers_str += str(token_val)

            buf["NUMBERS"].append(numbers_str)
            buf["SHORT_WORDS"].append(short_words_str)
        except tokenize.TokenError as error:
            print(f"Oops! Something went wrong!Reason: {error}")

    @staticmethod
    def text_processing(text: str) -> str:

        """Метод для обработки текста токена перед включением его в буферы экземпляра"""

        char_mapping = {
            ord(' '): '',
            ord('\n'): '',
            ord('\t'): '',
            ord('\r'): '',
        }
        processed_text = unicodedata.normalize("NFKC", text.strip().lower().translate(char_mapping))
        return processed_text

    @staticmethod
    def levenstein_distance(source_string: str, edited_string: str) -> int:

        """Метод для нахождения расстояния редактирования по алгоритму Левенштейна"""

        distance_matrix = [
            [
                row_val + col_val if not row_val * col_val else 0
                for col_val in range(len(edited_string) + 1)
            ]
            for row_val in range(len(source_string) + 1)
        ]

        for i in range(1, len(source_string) + 1):
            for j in range(1, len(edited_string) + 1):
                distance_matrix[i][j] = min(
                    1 + distance_matrix[i - 1][j],
                    1 + distance_matrix[i][j - 1],
                    int(not source_string[i - 1] == edited_string[j - 1]) + distance_matrix[i - 1][j - 1]
                )

        return distance_matrix[len(source_string)][len(edited_string)]

    def _get_source_text_length(self) -> int:

        """Метод для получения длины исходного текста"""

        length = int()
        for keyword in self._source_content:
            for string in self._source_content[keyword]:
                length += len(string)
        return length

    def _compare(self, source_stat: list[tuple], edited_stat: list[tuple], source_text_length: int) -> float:

        """Метод для сравнения содержимого словарей source_statistics и edited_statistics"""

        difference_degree = float()
        category_length = float()
        relative_coefficient = float()
        try:
            for source_word, _ in source_stat:
                category_length += len(source_word)
            relative_coefficient = category_length / source_text_length

            for source_word, source_word_frequency in source_stat:
                for edited_word, edit_word_frequency in edited_stat:
                    edit_distance = self.levenstein_distance(source_word, edited_word)
                    if 0 < edit_distance < len(source_word) / 5:
                        difference_degree += (edit_distance * edit_word_frequency) / (
                                len(source_word) * source_word_frequency)

            return relative_coefficient * difference_degree
        except ValueError:
            return difference_degree

    def run(self, source_filename: str, edited_filename: str) -> float:

        """
        Метод для запуска алгоритма компаратора:
        тексты полученных файлов разбиваются на токены, обрабатываются и помещаются в словари,
        содержащие информацию о частоте употребления каждого из слов определенной категории.
        Значения словарей (Counter_obj.most_common()) сравниваются следующим образом:
        во внешнем цикле for происходит итерация по списку,
        содержащему слова исходного текста и частоту их употребления,
        во внутреннем for итерируемся по другому списку, фиксируем места,
        где были правки/добавления/удаления,
        ищем отношение редакционного расстояния к длине исходного слова с учетом частоты употребления.
        Коэффициент разности текстов difference_degree умножается на относительный коэффициент,
        учитывающий отношение всех слов категории к длине текста
        """

        self._file_process(filename=source_filename, buf=self._source_content)
        self._file_process(filename=edited_filename, buf=self._edited_content)

        if self._source_content == self._edited_content:
            self._result = 1
            return self._result

        source_text_length = self._get_source_text_length()

        source_statistics = {
            "STRINGS_STAT": Counter(self._source_content["STRINGS"]).most_common(),
            "DOCSTRINGS_STAT": Counter(self._source_content["DOCSTRINGS"]).most_common(),
            "NUMBERS_STAT": Counter(self._source_content["NUMBERS"]).most_common(),
            "COMMENTS_STAT": Counter(self._source_content["COMMENTS"]).most_common(),
            "WORDS_STAT": Counter(self._source_content["WORDS"]).most_common(),
            "SHORT_WORDS_STAT": [Counter(self._source_content["SHORT_WORDS"]).most_common()]
        }

        edited_statistics = {
            "STRINGS_STAT": Counter(self._edited_content["STRINGS"]).most_common(),
            "DOCSTRINGS_STAT": Counter(self._edited_content["DOCSTRINGS"]).most_common(),
            "NUMBERS_STAT": Counter(self._edited_content["NUMBERS"]).most_common(),
            "COMMENTS_STAT": Counter(self._edited_content["COMMENTS"]).most_common(),
            "WORDS_STAT": Counter(self._edited_content["WORDS"]).most_common(),
            "SHORT_WORDS_STAT": Counter(self._edited_content["SHORT_WORDS"]).most_common()
        }

        summary_difference = float()

        for source_stat_val, edited_stat_val in zip(source_statistics.values(), edited_statistics.values()):
            summary_difference += self._compare(source_stat_val, edited_stat_val, source_text_length)

        self._result = abs(round(1 - summary_difference, 3))

        for key in self._source_content:
            self._source_content[key].clear()
        for key in self._edited_content:
            self._edited_content[key].clear()

        return self._result

    def main(self, *, input_filename: str, output_filename: str) -> None:
        """Метод для запуска компаратора в качестве скрипта"""
        try:
            with open(input_filename, 'r', encoding="utf-8") as file:
                for filenames_string in file:
                    list_of_filenames = filenames_string.split()
                    self.run(*list_of_filenames)
                    self.output(script_output_filename=output_filename)
        except TypeError:
            print("Comparator has not found files to compare")

    def output(self, *, script_output_filename='', output_filename='') -> None:
        """Метод для вывода резульата в файл output.txt"""
        filename = script_output_filename or output_filename
        with open(filename, 'a+', encoding="utf-8") as file:
            file.write(f"{self._result}\n")


if __name__ == "__main__":
    parser = ArgParser()
    comp = Comparator(skip_docs_and_comments=parser.parameters.d)
    comp.main(
        input_filename=parser.parameters.input_file,
        output_filename=parser.parameters.output_file
    )
