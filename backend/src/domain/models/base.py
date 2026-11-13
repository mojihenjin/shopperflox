from dataclasses import asdict, dataclass


@dataclass(slots=True)
class BaseDomain:
    def to_dict(self, exclude: set | None = None):
        exclude = exclude or set()

        return {
            key: value
            for key, value in asdict(self).items()
            if key not in exclude and not callable(value)
        }
