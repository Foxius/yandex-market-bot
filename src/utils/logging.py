# src/utils/logging.py
import logging
import colorlog

class PlatformColorFilter(logging.Filter):
    """Custom filter to apply colors based on platform prefix in the message."""
    def filter(self, record):
        if "[yandex]" in record.msg:
            record.log_color = "yellow"  # Желтый для [yandex]
        elif "[ozon]" in record.msg:
            record.log_color = "cyan"    # Голубой (синий) для [ozon]
        else:
            # Используем стандартные цвета для уровня логирования, если нет платформы
            level_colors = {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
            record.log_color = level_colors.get(record.levelname, 'white')
        return True

def setup_logging() -> logging.Logger:
    """Configure colored logging for the application.

    Returns:
        logging.Logger: Configured logger instance.
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        log_colors={  # Базовые цвета для уровней логирования (если платформа не указана)
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    ))
    
    # Добавляем фильтр для динамической раскраски
    handler.addFilter(PlatformColorFilter())
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logging()