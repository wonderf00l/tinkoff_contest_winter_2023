Предполагается, что в аргументах командной строки прописываются пути, аналогичные демонстрационным, помимо этого, принимается опциональный параметр -d, при указании которого пропускаются комментарии и docstrings.

Примеры вызова: python compare.py input.txt scores.txt 
                python compare.py input.txt scores.txt -d=true
              
Реализована возможность импорта экземпляра класса Comparator и использование в других скриптах.
Пример импорта и использования:

from compare.py import Comparator

comparator = Comparator(skip_docs_and_comments=False)
similarity_degree = comparator.run(source_filename, edited_filename)

P.S. Хотелось бы получить актуальные прикладные знания в области ML и задать специалисатм Тинькофф вопросы касательно способов реализации собственных идей и проектов в этой области.
я в telegram: @w0nderf00l
