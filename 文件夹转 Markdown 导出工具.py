#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹 <-> Markdown 互转工具（多语言版）
支持：简体中文 / English / Français / Español / Русский / العربية
"""

import os
import re
import threading
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ==================== 多语言配置 ====================
LANGS = [
    ('zh', '简体中文'),
    ('en', 'English'),
    ('fr', 'Français'),
    ('es', 'Español'),
    ('ru', 'Русский'),
    ('ar', 'العربية'),
]
LANG_BY_LABEL = {label: code for code, label in LANGS}
LABEL_BY_LANG = {code: label for code, label in LANGS}
CURRENT_LANG = 'zh'

TRANSLATIONS = {
    'zh': {
        'app_title': '文件夹 <-> Markdown 互转工具',
        'lang_label': '语言：',
        'tab_export': '  导出（文件夹 → Markdown）  ',
        'tab_restore': '  还原（Markdown → 文件夹）  ',
        'btn_gen_ai_guide': '生成 AI 规范文件（指导其他 AI 输出格式）',
        'lbl_target_folder': '目标文件夹：',
        'btn_choose': '选择…',
        'frame_options': '选项',
        'chk_include_hidden': '包含隐藏文件 / 文件夹（以 . 开头）',
        'lbl_max_size': '单文件内容大小上限（MB，0 = 不限制）：',
        'lbl_split_size': '拆分阈值（MB，0 = 不拆分）：',
        'lbl_split_hint': '超过阈值时生成母文件 + 若干子文件',
        'btn_start_export': '开始导出',
        'btn_cancel': '取消',
        'frame_progress': '进度',
        'status_ready': '就绪',
        'dlg_save_mother_title': '保存母文件（Markdown）',
        'ft_md': 'Markdown 文件',
        'ft_all': '所有文件',
        'lbl_restore_info': '选择由本工具导出的 Markdown 文件（可多选）。'
                            '若选择母文件，将自动发现同目录下的所有子文件。',
        'btn_choose_md': '选择 md 文件…',
        'btn_clear_list': '清空列表',
        'lbl_selected_count': '已选 {n} 个文件',
        'frame_selected_files': '已选文件',
        'lbl_restore_to': '还原到文件夹：',
        'chk_auto_discover': '自动发现同目录下的子文件（母文件拆分场景）',
        'btn_start_restore': '开始还原',
        'dlg_choose_md_title': '选择要还原的 md 文件',
        'dlg_choose_target_title': '选择还原到的文件夹',
        'warn_title': '提示',
        'warn_no_folder': '请先选择目标文件夹。',
        'err_title': '错误',
        'err_invalid_folder': '所选路径不是有效文件夹。',
        'err_size_param': '大小参数必须是 ≥ 0 的数字。',
        'warn_no_md': '请先选择要还原的 md 文件。',
        'warn_no_target': '请选择还原到的目标文件夹。',
        'confirm_title': '确认',
        'confirm_overwrite': '将把 md 文件内容还原到：\n{path}\n\n'
                             '同名文件会被覆盖，是否继续？',
        'info_done_title': '完成',
        'info_export_done': '导出完成！\n\n文件数：{files}\n'
                            '文件夹数：{dirs}\n\n输出文件：\n{path}',
        'info_export_done_split': '导出完成（已拆分）！\n\n文件数：{files}\n'
                                  '文件夹数：{dirs}\n子文件数：{parts}\n\n'
                                  '母文件：\n{path}',
        'info_restore_done': '还原完成！\n\n目标文件夹：\n{path}\n\n'
                             '写入文件数：{written} / {total}\n'
                             '扫描 md 文件：{scanned} 个{skip}',
        'err_export_failed': '导出失败：{err}',
        'err_restore_failed': '还原失败：{err}',
        'status_cancelling': '正在取消…',
        'status_error': '发生错误',
        'status_done_split': '完成：{files} 个文件 / {dirs} 个文件夹，'
                             '拆分为 {parts} 个子文件',
        'status_done': '完成：{files} 个文件，{dirs} 个文件夹',
        'status_done_restore': '完成：写入 {written} / {total} 个文件',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ 母文件：{path}',
        'log_exported_to': '✅ 已导出到：{path}',
        'log_restore_target': '✅ 还原目标：{path}',
        'log_scanned_md': '   参与解析的 md 文件：',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ 跳过：{msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': '保存 AI 规范文件',
        'info_guide_saved': 'AI 规范文件已保存：\n{path}\n\n'
                            '把它发给其他 AI，它们就能按格式输出可还原的 Markdown。',
        'err_guide_save_failed': '保存失败：{err}',
        'default_guide_filename': 'AI输出规范_文件夹Markdown格式.md',
        'skip_suffix': '，跳过 {n} 项',
    },
    'en': {
        'app_title': 'Folder <-> Markdown Converter',
        'lang_label': 'Language:',
        'tab_export': '  Export (Folder → Markdown)  ',
        'tab_restore': '  Restore (Markdown → Folder)  ',
        'btn_gen_ai_guide': 'Generate AI Guide (for other AI output format)',
        'lbl_target_folder': 'Target folder:',
        'btn_choose': 'Choose…',
        'frame_options': 'Options',
        'chk_include_hidden': 'Include hidden files / folders (starting with .)',
        'lbl_max_size': 'Max file content size (MB, 0 = no limit):',
        'lbl_split_size': 'Split threshold (MB, 0 = no split):',
        'lbl_split_hint': 'Split into mother file + parts when exceeded',
        'btn_start_export': 'Start Export',
        'btn_cancel': 'Cancel',
        'frame_progress': 'Progress',
        'status_ready': 'Ready',
        'dlg_save_mother_title': 'Save mother file (Markdown)',
        'ft_md': 'Markdown files',
        'ft_all': 'All files',
        'lbl_restore_info': 'Select Markdown files exported by this tool '
                            '(multiple allowed). Selecting the mother file '
                            'will auto-discover all parts in the same folder.',
        'btn_choose_md': 'Choose md files…',
        'btn_clear_list': 'Clear list',
        'lbl_selected_count': '{n} file(s) selected',
        'frame_selected_files': 'Selected files',
        'lbl_restore_to': 'Restore to folder:',
        'chk_auto_discover': 'Auto-discover parts in the same folder '
                             '(mother file scenario)',
        'btn_start_restore': 'Start Restore',
        'dlg_choose_md_title': 'Choose md files to restore',
        'dlg_choose_target_title': 'Choose target folder',
        'warn_title': 'Notice',
        'warn_no_folder': 'Please choose a target folder first.',
        'err_title': 'Error',
        'err_invalid_folder': 'Selected path is not a valid folder.',
        'err_size_param': 'Size parameters must be numbers >= 0.',
        'warn_no_md': 'Please choose md files to restore.',
        'warn_no_target': 'Please choose a target folder.',
        'confirm_title': 'Confirm',
        'confirm_overwrite': 'Will restore md content to:\n{path}\n\n'
                             'Existing files will be overwritten. Continue?',
        'info_done_title': 'Done',
        'info_export_done': 'Export complete!\n\nFiles: {files}\n'
                            'Folders: {dirs}\n\nOutput file:\n{path}',
        'info_export_done_split': 'Export complete (split)!\n\nFiles: {files}\n'
                                  'Folders: {dirs}\nParts: {parts}\n\n'
                                  'Mother file:\n{path}',
        'info_restore_done': 'Restore complete!\n\nTarget folder:\n{path}\n\n'
                             'Files written: {written} / {total}\n'
                             'md files scanned: {scanned}{skip}',
        'err_export_failed': 'Export failed: {err}',
        'err_restore_failed': 'Restore failed: {err}',
        'status_cancelling': 'Cancelling…',
        'status_error': 'Error',
        'status_done_split': 'Done: {files} files / {dirs} folders, '
                             'split into {parts} parts',
        'status_done': 'Done: {files} files, {dirs} folders',
        'status_done_restore': 'Done: wrote {written} / {total} files',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ Mother file: {path}',
        'log_exported_to': '✅ Exported to: {path}',
        'log_restore_target': '✅ Restore target: {path}',
        'log_scanned_md': '   md files parsed:',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ Skipped: {msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': 'Save AI Guide',
        'info_guide_saved': 'AI Guide saved:\n{path}\n\n'
                            'Send it to other AIs so they can output a restorable Markdown.',
        'err_guide_save_failed': 'Save failed: {err}',
        'default_guide_filename': 'AI_Guide_Folder_Markdown_Format.md',
        'skip_suffix': ', {n} skipped',
    },
    'fr': {
        'app_title': 'Convertisseur Dossier <-> Markdown',
        'lang_label': 'Langue :',
        'tab_export': '  Exporter (Dossier → Markdown)  ',
        'tab_restore': '  Restaurer (Markdown → Dossier)  ',
        'btn_gen_ai_guide': 'Générer le guide IA (format de sortie pour autres IA)',
        'lbl_target_folder': 'Dossier cible :',
        'btn_choose': 'Choisir…',
        'frame_options': 'Options',
        'chk_include_hidden': 'Inclure les fichiers / dossiers cachés (commençant par .)',
        'lbl_max_size': 'Taille max. par fichier (Mo, 0 = illimité) :',
        'lbl_split_size': 'Seuil de fractionnement (Mo, 0 = aucun) :',
        'lbl_split_hint': 'Génère un fichier mère + sous-fichiers si dépassé',
        'btn_start_export': 'Lancer l\'export',
        'btn_cancel': 'Annuler',
        'frame_progress': 'Progression',
        'status_ready': 'Prêt',
        'dlg_save_mother_title': 'Enregistrer le fichier mère (Markdown)',
        'ft_md': 'Fichiers Markdown',
        'ft_all': 'Tous les fichiers',
        'lbl_restore_info': 'Sélectionnez les fichiers Markdown exportés par cet outil '
                            '(sélection multiple possible). En choisissant le fichier '
                            'mère, les sous-fichiers du même dossier seront détectés.',
        'btn_choose_md': 'Choisir les fichiers md…',
        'btn_clear_list': 'Vider la liste',
        'lbl_selected_count': '{n} fichier(s) sélectionné(s)',
        'frame_selected_files': 'Fichiers sélectionnés',
        'lbl_restore_to': 'Restaurer vers le dossier :',
        'chk_auto_discover': 'Découvrir automatiquement les sous-fichiers '
                             '(scénario fichier mère)',
        'btn_start_restore': 'Lancer la restauration',
        'dlg_choose_md_title': 'Choisir les fichiers md à restaurer',
        'dlg_choose_target_title': 'Choisir le dossier cible',
        'warn_title': 'Attention',
        'warn_no_folder': 'Veuillez d\'abord choisir un dossier cible.',
        'err_title': 'Erreur',
        'err_invalid_folder': 'Le chemin sélectionné n\'est pas un dossier valide.',
        'err_size_param': 'Les tailles doivent être des nombres >= 0.',
        'warn_no_md': 'Veuillez choisir des fichiers md à restaurer.',
        'warn_no_target': 'Veuillez choisir un dossier cible.',
        'confirm_title': 'Confirmation',
        'confirm_overwrite': 'Le contenu md sera restauré dans :\n{path}\n\n'
                             'Les fichiers existants seront écrasés. Continuer ?',
        'info_done_title': 'Terminé',
        'info_export_done': 'Export terminé !\n\nFichiers : {files}\n'
                            'Dossiers : {dirs}\n\nFichier de sortie :\n{path}',
        'info_export_done_split': 'Export terminé (fractionné) !\n\n'
                                  'Fichiers : {files}\nDossiers : {dirs}\n'
                                  'Sous-fichiers : {parts}\n\nFichier mère :\n{path}',
        'info_restore_done': 'Restauration terminée !\n\nDossier cible :\n{path}\n\n'
                             'Fichiers écrits : {written} / {total}\n'
                             'Fichiers md analysés : {scanned}{skip}',
        'err_export_failed': 'Échec de l\'export : {err}',
        'err_restore_failed': 'Échec de la restauration : {err}',
        'status_cancelling': 'Annulation…',
        'status_error': 'Erreur',
        'status_done_split': 'Terminé : {files} fichiers / {dirs} dossiers, '
                             'fractionné en {parts} parties',
        'status_done': 'Terminé : {files} fichiers, {dirs} dossiers',
        'status_done_restore': 'Terminé : {written} / {total} fichiers écrits',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ Fichier mère : {path}',
        'log_exported_to': '✅ Exporté vers : {path}',
        'log_restore_target': '✅ Cible de restauration : {path}',
        'log_scanned_md': '   fichiers md analysés :',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ Ignoré : {msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': 'Enregistrer le guide IA',
        'info_guide_saved': 'Guide IA enregistré :\n{path}\n\n'
                            'Envoyez-le à d\'autres IA pour qu\'elles produisent un Markdown restaurable.',
        'err_guide_save_failed': 'Échec de l\'enregistrement : {err}',
        'default_guide_filename': 'Guide_IA_Dossier_Markdown.md',
        'skip_suffix': ', {n} ignorés',
    },
    'es': {
        'app_title': 'Convertidor Carpeta <-> Markdown',
        'lang_label': 'Idioma:',
        'tab_export': '  Exportar (Carpeta → Markdown)  ',
        'tab_restore': '  Restaurar (Markdown → Carpeta)  ',
        'btn_gen_ai_guide': 'Generar guía IA (formato para otras IA)',
        'lbl_target_folder': 'Carpeta destino:',
        'btn_choose': 'Elegir…',
        'frame_options': 'Opciones',
        'chk_include_hidden': 'Incluir archivos / carpetas ocultos (que empiezan por .)',
        'lbl_max_size': 'Tamaño máx. por archivo (MB, 0 = sin límite):',
        'lbl_split_size': 'Umbral de división (MB, 0 = sin división):',
        'lbl_split_hint': 'Genera archivo madre + subarchivos si se supera',
        'btn_start_export': 'Iniciar exportación',
        'btn_cancel': 'Cancelar',
        'frame_progress': 'Progreso',
        'status_ready': 'Listo',
        'dlg_save_mother_title': 'Guardar archivo madre (Markdown)',
        'ft_md': 'Archivos Markdown',
        'ft_all': 'Todos los archivos',
        'lbl_restore_info': 'Seleccione los archivos Markdown exportados por esta '
                            'herramienta (se permite selección múltiple). Al elegir '
                            'el archivo madre se detectarán los subarchivos del mismo directorio.',
        'btn_choose_md': 'Elegir archivos md…',
        'btn_clear_list': 'Vaciar lista',
        'lbl_selected_count': '{n} archivo(s) seleccionado(s)',
        'frame_selected_files': 'Archivos seleccionados',
        'lbl_restore_to': 'Restaurar a la carpeta:',
        'chk_auto_discover': 'Detectar automáticamente subarchivos '
                             '(escenario archivo madre)',
        'btn_start_restore': 'Iniciar restauración',
        'dlg_choose_md_title': 'Elegir archivos md a restaurar',
        'dlg_choose_target_title': 'Elegir carpeta destino',
        'warn_title': 'Aviso',
        'warn_no_folder': 'Primero elija una carpeta destino.',
        'err_title': 'Error',
        'err_invalid_folder': 'La ruta seleccionada no es una carpeta válida.',
        'err_size_param': 'Los tamaños deben ser números >= 0.',
        'warn_no_md': 'Elija archivos md para restaurar.',
        'warn_no_target': 'Elija una carpeta destino.',
        'confirm_title': 'Confirmar',
        'confirm_overwrite': 'Se restaurará el contenido md en:\n{path}\n\n'
                             'Los archivos existentes serán sobrescritos. ¿Continuar?',
        'info_done_title': 'Hecho',
        'info_export_done': '¡Exportación completada!\n\nArchivos: {files}\n'
                            'Carpetas: {dirs}\n\nArchivo de salida:\n{path}',
        'info_export_done_split': '¡Exportación completada (dividida)!\n\n'
                                  'Archivos: {files}\nCarpetas: {dirs}\n'
                                  'Subarchivos: {parts}\n\nArchivo madre:\n{path}',
        'info_restore_done': '¡Restauración completada!\n\nCarpeta destino:\n{path}\n\n'
                             'Archivos escritos: {written} / {total}\n'
                             'Archivos md analizados: {scanned}{skip}',
        'err_export_failed': 'Fallo en la exportación: {err}',
        'err_restore_failed': 'Fallo en la restauración: {err}',
        'status_cancelling': 'Cancelando…',
        'status_error': 'Error',
        'status_done_split': 'Hecho: {files} archivos / {dirs} carpetas, '
                             'dividido en {parts} partes',
        'status_done': 'Hecho: {files} archivos, {dirs} carpetas',
        'status_done_restore': 'Hecho: {written} / {total} archivos escritos',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ Archivo madre: {path}',
        'log_exported_to': '✅ Exportado a: {path}',
        'log_restore_target': '✅ Destino de restauración: {path}',
        'log_scanned_md': '   archivos md analizados:',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ Omitido: {msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': 'Guardar guía IA',
        'info_guide_saved': 'Guía IA guardada:\n{path}\n\n'
                            'Envíela a otras IA para que produzcan un Markdown restaurable.',
        'err_guide_save_failed': 'Fallo al guardar: {err}',
        'default_guide_filename': 'Guia_IA_Carpeta_Markdown.md',
        'skip_suffix': ', {n} omitidos',
    },
    'ru': {
        'app_title': 'Конвертер Папка <-> Markdown',
        'lang_label': 'Язык:',
        'tab_export': '  Экспорт (Папка → Markdown)  ',
        'tab_restore': '  Восстановление (Markdown → Папка)  ',
        'btn_gen_ai_guide': 'Создать ИИ-руководство (формат для других ИИ)',
        'lbl_target_folder': 'Целевая папка:',
        'btn_choose': 'Выбрать…',
        'frame_options': 'Параметры',
        'chk_include_hidden': 'Включать скрытые файлы / папки (начинающиеся с .)',
        'lbl_max_size': 'Макс. размер файла (МБ, 0 = без ограничений):',
        'lbl_split_size': 'Порог разбиения (МБ, 0 = не разбивать):',
        'lbl_split_hint': 'При превышении создаёт основной файл + части',
        'btn_start_export': 'Начать экспорт',
        'btn_cancel': 'Отмена',
        'frame_progress': 'Прогресс',
        'status_ready': 'Готов',
        'dlg_save_mother_title': 'Сохранить основной файл (Markdown)',
        'ft_md': 'Файлы Markdown',
        'ft_all': 'Все файлы',
        'lbl_restore_info': 'Выберите файлы Markdown, созданные этим инструментом '
                            '(можно несколько). Если выбрать основной файл, '
                            'части в той же папке будут найдены автоматически.',
        'btn_choose_md': 'Выбрать md файлы…',
        'btn_clear_list': 'Очистить список',
        'lbl_selected_count': 'Выбрано файлов: {n}',
        'frame_selected_files': 'Выбранные файлы',
        'lbl_restore_to': 'Восстановить в папку:',
        'chk_auto_discover': 'Автоматически находить части в той же папке '
                             '(сценарий основного файла)',
        'btn_start_restore': 'Начать восстановление',
        'dlg_choose_md_title': 'Выбрать md файлы для восстановления',
        'dlg_choose_target_title': 'Выбрать целевую папку',
        'warn_title': 'Внимание',
        'warn_no_folder': 'Сначала выберите целевую папку.',
        'err_title': 'Ошибка',
        'err_invalid_folder': 'Выбранный путь не является папкой.',
        'err_size_param': 'Размеры должны быть числами >= 0.',
        'warn_no_md': 'Выберите md файлы для восстановления.',
        'warn_no_target': 'Выберите целевую папку.',
        'confirm_title': 'Подтверждение',
        'confirm_overwrite': 'Содержимое md будет восстановлено в:\n{path}\n\n'
                             'Существующие файлы будут перезаписаны. Продолжить?',
        'info_done_title': 'Готово',
        'info_export_done': 'Экспорт завершён!\n\nФайлов: {files}\n'
                            'Папок: {dirs}\n\nВыходной файл:\n{path}',
        'info_export_done_split': 'Экспорт завершён (с разбиением)!\n\n'
                                  'Файлов: {files}\nПапок: {dirs}\n'
                                  'Частей: {parts}\n\nОсновной файл:\n{path}',
        'info_restore_done': 'Восстановление завершено!\n\nЦелевая папка:\n{path}\n\n'
                             'Записано файлов: {written} / {total}\n'
                             'Просканировано md: {scanned}{skip}',
        'err_export_failed': 'Ошибка экспорта: {err}',
        'err_restore_failed': 'Ошибка восстановления: {err}',
        'status_cancelling': 'Отмена…',
        'status_error': 'Ошибка',
        'status_done_split': 'Готово: {files} файлов / {dirs} папок, '
                             'разбито на {parts} частей',
        'status_done': 'Готово: {files} файлов, {dirs} папок',
        'status_done_restore': 'Готово: записано {written} / {total} файлов',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ Основной файл: {path}',
        'log_exported_to': '✅ Экспортировано в: {path}',
        'log_restore_target': '✅ Цель восстановления: {path}',
        'log_scanned_md': '   просканированные md файлы:',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ Пропущено: {msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': 'Сохранить ИИ-руководство',
        'info_guide_saved': 'ИИ-руководство сохранено:\n{path}\n\n'
                            'Отправьте его другим ИИ, чтобы они могли выдать восстановимый Markdown.',
        'err_guide_save_failed': 'Ошибка сохранения: {err}',
        'default_guide_filename': 'AI_Guide_Folder_Markdown_RU.md',
        'skip_suffix': ', пропущено {n}',
    },
    'ar': {
        'app_title': 'محول المجلد <-> Markdown',
        'lang_label': 'اللغة:',
        'tab_export': '  تصدير (مجلد → Markdown)  ',
        'tab_restore': '  استعادة (Markdown → مجلد)  ',
        'btn_gen_ai_guide': 'إنشاء دليل الذكاء الاصطناعي (لتنسيق مخرجات الذكاء الاصطناعي)',
        'lbl_target_folder': 'المجلد الهدف:',
        'btn_choose': 'اختر…',
        'frame_options': 'الخيارات',
        'chk_include_hidden': 'تضمين الملفات / المجلدات المخفية (التي تبدأ بـ .)',
        'lbl_max_size': 'الحد الأقصى لحجم الملف (ميجابايت، 0 = بلا حد):',
        'lbl_split_size': 'عتبة التقسيم (ميجابايت، 0 = بلا تقسيم):',
        'lbl_split_hint': 'ينشئ ملفًا رئيسيًا + ملفات فرعية عند التجاوز',
        'btn_start_export': 'ابدأ التصدير',
        'btn_cancel': 'إلغاء',
        'frame_progress': 'التقدم',
        'status_ready': 'جاهز',
        'dlg_save_mother_title': 'حفظ الملف الرئيسي (Markdown)',
        'ft_md': 'ملفات Markdown',
        'ft_all': 'كل الملفات',
        'lbl_restore_info': 'اختر ملفات Markdown المُصدَّرة بواسطة هذه الأداة '
                            '(يُسمح باختيار متعدد). عند اختيار الملف الرئيسي '
                            'سيتم اكتشاف الملفات الفرعية تلقائيًا.',
        'btn_choose_md': 'اختر ملفات md…',
        'btn_clear_list': 'مسح القائمة',
        'lbl_selected_count': 'تم اختيار {n} ملف',
        'frame_selected_files': 'الملفات المختارة',
        'lbl_restore_to': 'الاستعادة إلى مجلد:',
        'chk_auto_discover': 'اكتشاف الملفات الفرعية تلقائيًا في نفس المجلد '
                             '(سيناريو الملف الرئيسي)',
        'btn_start_restore': 'ابدأ الاستعادة',
        'dlg_choose_md_title': 'اختر ملفات md للاستعادة',
        'dlg_choose_target_title': 'اختر المجلد الهدف',
        'warn_title': 'تنبيه',
        'warn_no_folder': 'يرجى اختيار مجلد هدف أولاً.',
        'err_title': 'خطأ',
        'err_invalid_folder': 'المسار المختار ليس مجلدًا صالحًا.',
        'err_size_param': 'يجب أن تكون الأحجام أرقامًا >= 0.',
        'warn_no_md': 'يرجى اختيار ملفات md للاستعادة.',
        'warn_no_target': 'يرجى اختيار مجلد هدف.',
        'confirm_title': 'تأكيد',
        'confirm_overwrite': 'سيتم استعادة محتوى md إلى:\n{path}\n\n'
                             'سيتم استبدال الملفات الموجودة. هل تريد المتابعة؟',
        'info_done_title': 'تم',
        'info_export_done': 'اكتمل التصدير!\n\nالملفات: {files}\n'
                            'المجلدات: {dirs}\n\nالملف الناتج:\n{path}',
        'info_export_done_split': 'اكتمل التصدير (مع تقسيم)!\n\n'
                                  'الملفات: {files}\nالمجلدات: {dirs}\n'
                                  'الملفات الفرعية: {parts}\n\nالملف الرئيسي:\n{path}',
        'info_restore_done': 'اكتملت الاستعادة!\n\nالمجلد الهدف:\n{path}\n\n'
                             'الملفات المكتوبة: {written} / {total}\n'
                             'ملفات md المفحوصة: {scanned}{skip}',
        'err_export_failed': 'فشل التصدير: {err}',
        'err_restore_failed': 'فشل الاستعادة: {err}',
        'status_cancelling': 'جارٍ الإلغاء…',
        'status_error': 'خطأ',
        'status_done_split': 'تم: {files} ملف / {dirs} مجلد، '
                             'مقسم إلى {parts} أجزاء',
        'status_done': 'تم: {files} ملف، {dirs} مجلد',
        'status_done_restore': 'تم: كتابة {written} / {total} ملف',
        'status_progress': '[{cur}/{total}] {name}',
        'log_mother_file': '✅ الملف الرئيسي: {path}',
        'log_exported_to': '✅ تم التصدير إلى: {path}',
        'log_restore_target': '✅ هدف الاستعادة: {path}',
        'log_scanned_md': '   ملفات md المفحوصة:',
        'log_warn': '⚠ {msg}',
        'log_skip': '⚠ تم التخطي: {msg}',
        'log_branch': '   ├─ {path}',
        'dlg_save_guide_title': 'حفظ دليل الذكاء الاصطناعي',
        'info_guide_saved': 'تم حفظ دليل الذكاء الاصطناعي:\n{path}\n\n'
                            'أرسله إلى أنظمة ذكاء اصطناعي أخرى لتُخرج Markdown قابلًا للاستعادة.',
        'err_guide_save_failed': 'فشل الحفظ: {err}',
        'default_guide_filename': 'AI_Guide_Folder_Markdown_AR.md',
        'skip_suffix': '، تم تخطي {n}',
    },
}


def tr(key, **kw):
    d = TRANSLATIONS.get(CURRENT_LANG) or TRANSLATIONS['zh']
    s = d.get(key) or TRANSLATIONS['zh'].get(key) or key
    try:
        return s.format(**kw) if kw else s
    except Exception:
        return s


# ==================== 语言映射 ====================
EXT_LANG_MAP = {
    '.py': 'python', '.pyw': 'python',
    '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.ts': 'typescript', '.tsx': 'tsx', '.jsx': 'jsx',
    '.java': 'java', '.kt': 'kotlin', '.scala': 'scala',
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
    '.cs': 'csharp', '.go': 'go', '.rs': 'rust',
    '.rb': 'ruby', '.php': 'php', '.swift': 'swift',
    '.html': 'html', '.htm': 'html', '.xhtml': 'html',
    '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
    '.json': 'json', '.jsonc': 'json', '.xml': 'xml', '.svg': 'xml',
    '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
    '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini',
    '.md': 'markdown', '.markdown': 'markdown',
    '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
    '.bat': 'batch', '.cmd': 'batch', '.ps1': 'powershell',
    '.sql': 'sql', '.r': 'r', '.lua': 'lua', '.pl': 'perl',
    '.vue': 'vue', '.svelte': 'svelte',
    '.txt': 'text', '.log': 'text', '.csv': 'csv', '.tsv': 'tsv',
    '.tex': 'latex', '.bib': 'bibtex',
    '.asm': 'asm', '.s': 'asm',
    '.dart': 'dart', '.ex': 'elixir', '.exs': 'elixir',
    '.erl': 'erlang', '.hrl': 'erlang',
    '.clj': 'clojure', '.cljs': 'clojure',
    '.hs': 'haskell', '.ml': 'ocaml', '.nim': 'nim', '.zig': 'zig',
    '.gradle': 'groovy', '.groovy': 'groovy',
    '.proto': 'protobuf', '.graphql': 'graphql', '.gql': 'graphql',
}
SPECIAL_FILES = {
    'dockerfile': 'dockerfile', 'makefile': 'makefile',
    'gnumakefile': 'makefile', 'cmakelists.txt': 'cmake',
    '.gitignore': 'gitignore', '.gitattributes': 'gitignore',
    '.env': 'bash', '.editorconfig': 'ini', '.npmrc': 'ini',
    'go.mod': 'go', 'cargo.toml': 'toml', 'cargo.lock': 'toml',
}


# ==================== 工具函数 ====================
def get_language(fpath: Path) -> str:
    name_lower = fpath.name.lower()
    if name_lower in SPECIAL_FILES:
        return SPECIAL_FILES[name_lower]
    return EXT_LANG_MAP.get(fpath.suffix.lower(), '')


def is_binary_file(fpath: Path, blocksize: int = 8192) -> bool:
    try:
        with open(fpath, 'rb') as f:
            chunk = f.read(blocksize)
        return b'\x00' in chunk if chunk else False
    except (OSError, PermissionError):
        return True


def read_text_file(fpath: Path):
    raw = fpath.read_bytes()
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8(replace)'


def safe_fence(content: str) -> str:
    max_run = cur = 0
    for ch in content:
        if ch == '`':
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 0
    return '`' * max(3, max_run + 1)


def human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n} B" if unit == 'B' else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def walk_sorted(root: Path, include_hidden: bool = False):
    def _walk(d: Path):
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            return
        if not include_hidden:
            entries = [e for e in entries if not e.name.startswith('.')]
        dirs = sorted((e for e in entries if e.is_dir()), key=lambda x: x.name.lower())
        files = sorted((e for e in entries if e.is_file()), key=lambda x: x.name.lower())
        for sub in dirs:
            yield from _walk(sub)
        for f in files:
            yield f
    yield from _walk(root)


def generate_tree(root: Path, include_hidden: bool = False) -> str:
    lines = [f"{root.name}/"]

    def _walk(d: Path, prefix: str):
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            return
        if not include_hidden:
            entries = [e for e in entries if not e.name.startswith('.')]
        dirs = sorted((e for e in entries if e.is_dir()), key=lambda x: x.name.lower())
        files = sorted((e for e in entries if e.is_file()), key=lambda x: x.name.lower())
        items = dirs + files
        for i, item in enumerate(items):
            last = (i == len(items) - 1)
            connector = "└── " if last else "├── "
            suffix = "/" if item.is_dir() else ""
            lines.append(f"{prefix}{connector}{item.name}{suffix}")
            if item.is_dir():
                _walk(item, prefix + ("    " if last else "│   "))

    _walk(root, "")
    return "\n".join(lines)


def count_dirs(root: Path, include_hidden: bool = False) -> int:
    n = 0
    for _, dirnames, _ in os.walk(root):
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        n += len(dirnames)
    return n


# ==================== 导出：内容块 ====================
def _build_header(root_dir, total, dir_count, include_hidden,
                  max_size_mb, split_size_mb) -> str:
    s = []
    s.append(f"# {root_dir.name}\n\n")
    s.append(f"- root: `{root_dir}`\n")
    s.append(f"- exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    s.append(f"- files: {total}\n")
    s.append(f"- folders: {dir_count}\n")
    s.append(f"- include_hidden: {include_hidden}\n")
    s.append(f"- max_file_mb: {max_size_mb}\n")
    s.append(f"- split_mb: {split_size_mb}\n\n")
    return "".join(s)


def _file_block(idx, fpath, rel, size, binary, max_bytes) -> str:
    out = []
    out.append(f"### {idx}. `{rel.as_posix()}`\n\n")
    out.append(f"- name: `{fpath.name}`\n")
    out.append(f"- rel: `{rel.as_posix()}`\n")
    out.append(f"- abs: `{fpath}`\n")
    out.append(f"- size: {human_size(size)}\n\n")

    if binary:
        out.append("> binary file, no content exported.\n\n---\n\n")
        return "".join(out)
    if max_bytes and size > max_bytes:
        out.append(f"> file too large ({human_size(size)}), content skipped.\n\n---\n\n")
        return "".join(out)

    try:
        content, enc = read_text_file(fpath)
    except Exception as e:
        out.append(f"> read failed: `{e}`\n\n---\n\n")
        return "".join(out)

    lang = get_language(fpath)
    fence = safe_fence(content)
    out.append(f"<!-- encoding: {enc} -->\n\n")
    out.append(f"{fence}{lang}\n")
    out.append(content)
    if not content.endswith('\n'):
        out.append('\n')
    out.append(f"{fence}\n\n---\n\n")
    return "".join(out)


# ==================== 导出主逻辑 ====================
def generate_markdown(root_dir, out_path,
                      include_hidden=False, max_size_mb=10.0,
                      split_size_mb=0.0,
                      progress_cb=None, cancel_event=None) -> dict:
    root_dir = Path(root_dir).resolve()
    out_path = Path(out_path).resolve()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0
    split_bytes = int(split_size_mb * 1024 * 1024) if split_size_mb > 0 else 0

    all_files = list(walk_sorted(root_dir, include_hidden))
    total = len(all_files)
    dir_count = count_dirs(root_dir, include_hidden)

    file_info = []
    for fpath in all_files:
        try:
            rel = fpath.relative_to(root_dir)
        except ValueError:
            rel = fpath
        try:
            size = fpath.stat().st_size
        except OSError:
            size = 0
        binary = is_binary_file(fpath)
        content_size = 260 if (binary or (max_bytes and size > max_bytes)) else size + 420
        file_info.append({'path': fpath, 'rel': rel, 'size': size,
                          'binary': binary, 'content_size': content_size})

    tree_text = generate_tree(root_dir, include_hidden)
    header_text = _build_header(root_dir, total, dir_count,
                                include_hidden, max_size_mb, split_size_mb)
    header_size = len((header_text + tree_text).encode('utf-8')) + 4000
    total_content_size = sum(fi['content_size'] for fi in file_info)

    need_split = split_bytes > 0 and (header_size + total_content_size) > split_bytes
    base_dir = out_path.parent
    base_name = out_path.stem
    parts_written = []
    part_meta = []

    def _write_single(fp):
        fp.write(header_text)
        fp.write("---\n\n## 1. Tree\n\n```\n")
        fp.write(tree_text)
        fp.write("\n```\n\n---\n\n## 2. Contents\n\n")
        for idx, fi in enumerate(file_info, 1):
            if cancel_event and cancel_event.is_set():
                fp.write("\n> cancelled\n")
                break
            if progress_cb:
                progress_cb(idx, total, fi['rel'].as_posix())
            fp.write(_file_block(idx, fi['path'], fi['rel'],
                                 fi['size'], fi['binary'], max_bytes))

    chunks = []
    if need_split:
        part_reserve = 400
        cur_start = 0
        cur_size = part_reserve
        for i, fi in enumerate(file_info):
            bs = fi['content_size']
            if i > cur_start and (cur_size + bs) > split_bytes:
                chunks.append((cur_start, i))
                cur_start = i
                cur_size = part_reserve
            cur_size += bs
        if cur_start < len(file_info):
            chunks.append((cur_start, len(file_info)))
        if len(chunks) <= 1:
            need_split = False

    if not need_split:
        with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
            _write_single(fp)
        return {'files': total, 'dirs': dir_count,
                'output': str(out_path), 'parts': [], 'split': False}

    n_parts = len(chunks)
    width = max(2, len(str(n_parts)))
    for part_idx, (start, end) in enumerate(chunks, 1):
        if cancel_event and cancel_event.is_set():
            break
        part_name = f"{base_name}_part{part_idx:0{width}d}.md"
        part_path = base_dir / part_name
        parts_written.append(part_path)
        part_files = file_info[start:end]

        with open(part_path, 'w', encoding='utf-8', newline='\n') as fp:
            fp.write(f"# {root_dir.name} - part {part_idx}/{n_parts}\n\n")
            fp.write(f"- mother: [`{out_path.name}`](./{out_path.name})\n")
            fp.write(f"- range: {start + 1} - {end}\n")
            fp.write(f"- count: {len(part_files)}\n\n---\n\n")
            for local_i, fi in enumerate(part_files):
                global_idx = start + local_i + 1
                if cancel_event and cancel_event.is_set():
                    fp.write("\n> cancelled\n")
                    break
                if progress_cb:
                    progress_cb(global_idx, total, fi['rel'].as_posix())
                fp.write(_file_block(global_idx, fi['path'], fi['rel'],
                                     fi['size'], fi['binary'], max_bytes))

        part_meta.append({'name': part_name, 'start': start + 1, 'end': end,
                          'count': len(part_files)})

    with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(header_text)
        fp.write("---\n\n## 1. Tree\n\n```\n")
        fp.write(tree_text)
        fp.write("\n```\n\n---\n\n## 2. Index\n\n")
        fp.write(f"Content exceeded split threshold ({split_size_mb} MB), "
                 f"split into **{n_parts}** parts:\n\n")
        fp.write("| Part | Range | Count | Link |\n")
        fp.write("|:---|:---|---:|:---|\n")
        for m in part_meta:
            fp.write(f"| `{m['name']}` | {m['start']} - {m['end']} "
                     f"| {m['count']} | [Open](./{m['name']}) |\n")
        fp.write("\n> This mother file contains tree & index. "
                 "See links above for actual contents.\n")

    return {'files': total, 'dirs': dir_count, 'output': str(out_path),
            'parts': [str(p) for p in parts_written], 'split': True}


# ==================== 还原 ====================
HEADER_RE = re.compile(r'^###\s+\d+\.\s+`(.+?)`\s*$')
FENCE_RE = re.compile(r'^(`{3,})(\w*)\s*$')
ENC_RE = re.compile(r'<!--\s*(?:encoding|文件编码)[:：]\s*(.+?)\s*-->')
PART_REF_RE = re.compile(r'\|\s*`([^`]+?\.md)`\s*\|')


def parse_markdown_text(text: str):
    lines = text.split('\n')
    n = len(lines)
    i = 0
    while i < n:
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        rel_path = m.group(1).strip()
        i += 1
        encoding = 'utf-8'
        no_content = False

        while i < n:
            line = lines[i]
            if HEADER_RE.match(line):
                break
            em = ENC_RE.search(line)
            if em:
                encoding = em.group(1).strip()
                i += 1
                continue
            if FENCE_RE.match(line):
                break
            s = line.strip()
            if s.startswith('> '):
                no_content = True
                while i < n and not HEADER_RE.match(lines[i]):
                    if lines[i].strip() == '---':
                        i += 1
                        break
                    i += 1
                break
            i += 1

        if no_content:
            yield rel_path, None, encoding
            continue

        if i >= n:
            break
        fm = FENCE_RE.match(lines[i])
        if not fm:
            continue
        fence = fm.group(1)
        i += 1
        buf = []
        while i < n:
            if lines[i].rstrip() == fence:
                break
            buf.append(lines[i])
            i += 1
        if i < n:
            i += 1
        yield rel_path, '\n'.join(buf), encoding


def discover_parts(md_path: Path):
    try:
        text = md_path.read_text(encoding='utf-8')
    except Exception:
        return []
    found = []
    seen = set()
    for m in PART_REF_RE.finditer(text):
        name = m.group(1).strip()
        if not name.lower().endswith('.md'):
            continue
        if name in seen:
            continue
        seen.add(name)
        p = md_path.parent / name
        if p.exists() and p.is_file() and p != md_path:
            found.append(p)
    return found


def safe_join(base: Path, rel: str) -> Path:
    rel_norm = rel.replace('\\', '/').strip()
    if not rel_norm:
        raise ValueError("empty path")
    p = Path(rel_norm)
    if p.is_absolute():
        raise ValueError(f"absolute path not allowed: {rel}")
    clean_parts = []
    for part in p.parts:
        if part in ('', '.'):
            continue
        if part == '..':
            raise ValueError(f"path traversal not allowed: {rel}")
        if os.name == 'nt' and re.match(r'^(CON|PRN|AUX|NUL|COM\d|LPT\d)$',
                                        part, re.IGNORECASE):
            clean_parts.append('_' + part)
        else:
            clean_parts.append(part)
    if not clean_parts:
        raise ValueError(f"invalid path: {rel}")
    target = (base.joinpath(*clean_parts)).resolve()
    base_res = base.resolve()
    try:
        target.relative_to(base_res)
    except ValueError:
        raise ValueError(f"path escapes base: {rel}")
    return target


def restore_from_md(md_paths, target_dir: Path,
                    auto_discover_parts=True,
                    progress_cb=None, cancel_event=None) -> dict:
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    expanded = []
    seen_paths = set()
    for mp in md_paths:
        mp = Path(mp).resolve()
        if mp in seen_paths:
            continue
        seen_paths.add(mp)
        expanded.append(mp)
        if auto_discover_parts:
            for sub in discover_parts(mp):
                sub = sub.resolve()
                if sub not in seen_paths:
                    seen_paths.add(sub)
                    expanded.append(sub)

    entries = []
    errors = []
    for mp in expanded:
        try:
            text = mp.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"read {mp} failed: {e}")
            continue
        for rel, content, enc in parse_markdown_text(text):
            entries.append((rel, content, enc, mp.name))

    total = len(entries)
    written = 0
    skipped = []

    for idx, (rel, content, enc, src) in enumerate(entries, 1):
        if cancel_event and cancel_event.is_set():
            break
        if progress_cb:
            progress_cb(idx, total, rel)
        try:
            target = safe_join(target_dir, rel)
        except ValueError as e:
            skipped.append(f"{rel} ({e})")
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                target.write_bytes(b'')
            else:
                write_enc = 'utf-8' if enc.startswith('utf-8') else enc
                try:
                    target.write_text(content, encoding=write_enc)
                except LookupError:
                    target.write_text(content, encoding='utf-8')
            written += 1
        except Exception as e:
            skipped.append(f"{rel} (write failed: {e})")

    return {'written': written, 'total': total, 'target': str(target_dir),
            'files_scanned': [str(p) for p in expanded],
            'skipped': skipped, 'errors': errors}


# ==================== AI 规范文件（中文版） ====================
AI_GUIDE_MD = r'''# 文件夹 Markdown 格式规范（供 AI 参考）

本文件规范一种 Markdown 格式，用于描述一个文件夹的完整内容。
任何 AI 只要按本规范输出，用户即可用「文件夹转 Markdown 导出工具」的
还原功能，把 Markdown 还原成真实的文件夹结构与文件。

---

## 一、整体结构

Markdown 按顺序包含三部分，各部分之间用 `---` 分隔：

```
# 标题与元数据

## 一、目录结构
（代码块形式的目录树）

## 二、文件内容
### 1. `path/to/file1`
（元数据 + 内容）

### 2. `path/to/file2`
（元数据 + 内容）
```

---

## 二、标题与元数据

文件顶部是一级标题，随后是元数据列表：

```markdown
# 文件夹内容导出：myproject

- **根目录**：`/Users/me/myproject`
- **导出时间**：2026-01-01 12:00:00
- **文件总数**：5
- **文件夹总数**：2（不含根目录）
- **包含隐藏项**：否
- **单文件内容上限**：10.0 MB
- **拆分阈值**：不拆分
```

还原主要依据是每个文件块的路径，头部元数据供人类阅读。

---

## 三、目录结构（推荐，非必须）

`## 一、目录结构` 下面放一个代码块，内容是类似 `tree` 命令的目录树。
**还原时不依赖这部分**，但推荐提供，便于人类阅读。

```text
myproject/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md
```

---

## 四、文件内容块（核心）

`## 二、文件内容` 下面是每个文件的块。每个块按以下格式：

### 4.1 块头（强制）

```markdown
### N. `相对路径`
```

- `N` 从 1 开始，全局连续递增。
- 反引号里是**相对于根目录**的路径，使用 `/` 分隔。
- 路径不能是绝对路径，不能包含 `..`。

### 4.2 元数据（可选）

```markdown
- 文件名：`main.py`
- 相对路径：`src/main.py`
- 绝对路径：`/Users/me/myproject/src/main.py`
- 文件大小：1.23 KB
```

**只有 `### N. \`path\`` 这一行是强制的**，还原只看这一行和下面的代码块。

### 4.3 编码标记（可选）

若文件不是 UTF-8，可以加一个 HTML 注释：

```markdown
<!-- 文件编码：gbk -->
```

也兼容英文写法：`<!-- encoding: gbk -->`

### 4.4 内容（强制）

内容用**代码围栏**包裹，最少 3 个反引号。

````markdown
```python
print("hello")
```
````

语言标记（`python`、`js` 等）可选，还原时忽略。
**若文件内容本身包含连续反引号，围栏必须比内容里最长的连续反引号更长。**
例如内容里最多有 3 个连续反引号，围栏至少用 4 个。

### 4.5 块尾分隔（推荐）

每个文件块结尾加一行 `---`：

```markdown
### 1. `README.md`

- 文件名：`README.md`

```text
hello
```

---
```

---

## 五、二进制文件与超大文件

若文件是二进制或太大，可以不输出内容，只写说明：

```markdown
### 3. `logo.png`

- 文件名：`logo.png`
- 文件大小：12.34 KB

> 二进制文件，未导出内容。

---
```

还原时这种文件会被创建为空文件（占位）。

---

## 六、完整示例

````markdown
# 文件夹内容导出：demo

- **根目录**：`/tmp/demo`
- **导出时间**：2026-01-01 12:00:00
- **文件总数**：2
- **文件夹总数**：1（不含根目录）
- **包含隐藏项**：否
- **单文件内容上限**：10.0 MB
- **拆分阈值**：不拆分

---

## 一、目录结构

```
demo/
├── src/
│   └── main.py
└── README.md
```

---

## 二、文件内容

### 1. `README.md`

- 文件名：`README.md`
- 相对路径：`README.md`
- 绝对路径：`/tmp/demo/README.md`
- 文件大小：15 B

<!-- 文件编码：utf-8 -->

```text
# Demo
Hello, world!
```

---

### 2. `src/main.py`

- 文件名：`main.py`
- 相对路径：`src/main.py`
- 绝对路径：`/tmp/demo/src/main.py`
- 文件大小：20 B

<!-- 文件编码：utf-8 -->

```python
print("hello world")
```

---
````

---

## 七、AI 输出 Checklist

- [ ] 顶层有一级标题 `# ...`
- [ ] 至少包含 `## 二、文件内容` 段落
- [ ] 每个文件都以 `### N. \`相对路径\`` 开头
- [ ] `N` 从 1 连续递增
- [ ] 路径用正斜杠 `/`，不要用绝对路径，不要含 `..`
- [ ] 内容用代码围栏（至少 3 个反引号）包裹
- [ ] 若内容里含反引号，围栏要更长
- [ ] 二进制 / 超大文件用 `> 说明` 代替内容
- [ ] 各文件块之间用 `---` 分隔
- [ ] **整体不要再用一层代码块包住**（不要整个文件套在 ``` 里）

---

## 八、常见错误

| 错误 | 后果 | 修正 |
|---|---|---|
| 忘记写 `### N. \`path\`` | 该文件不会被还原 | 补上块头 |
| 路径是绝对路径 | 还原失败或越界 | 改成相对根目录的路径 |
| 围栏长度不够 | 内容被截断 | 用更长的围栏 |
| 整个 md 被包在 ``` 里 | 无法解析 | 不要整体包代码块 |
| 文件块之间没有 `---` | 一般不影响，但不清晰 | 加上 `---` |
| 路径里含 `..` | 被拒绝，跳过 | 改成正常相对路径 |

---

## 九、拆分输出（可选）

若内容很长，可拆分为一个母文件和多个子文件：

- **母文件**：包含元数据、目录结构、以及一个索引表：

  ```markdown
  | 子文件 | 覆盖文件序号 | 文件数 | 链接 |
  |:---|:---|---:|:---|
  | `xxx_part01.md` | 1 - 120 | 120 | [打开](./xxx_part01.md) |
  ```

- **子文件**：文件名形如 `<母文件名>_partNN.md`，
  内容为若干 `### N. \`path\`` 块（编号全局连续）。
  还原工具会自动发现并合并所有子文件。
'''


# ==================== AI 规范文件（英文版，供非中文界面使用） ====================
AI_GUIDE_MD_EN = r'''# Folder Markdown Format Specification (for AI Reference)

This document specifies a Markdown format that fully describes the contents
of a folder. Any AI that follows this specification can produce output that
users can feed into the "Folder <-> Markdown Converter" restore function to
recreate the real folder structure and file contents.

---

## 1. Overall Structure

The Markdown contains three sections in order, separated by `---`:

```
# Title and Metadata

## 1. Tree
(code block containing a directory tree)

## 2. Contents
### 1. `path/to/file1`
(metadata + content)

### 2. `path/to/file2`
(metadata + content)
```

---

## 2. Title and Metadata

The file starts with a level-1 heading followed by a metadata list:

```markdown
# myproject

- root: `/Users/me/myproject`
- exported: 2026-01-01 12:00:00
- files: 5
- folders: 2
- include_hidden: False
- max_file_mb: 10.0
- split_mb: 0
```

The restore process relies on each file block's path, not on the header.
Header metadata is for human readers.

---

## 3. Tree (Recommended, Not Required)

Under `## 1. Tree`, place a code block containing a `tree`-like directory
structure. **The restore function does not rely on this section**, but it is
recommended for readability.

```text
myproject/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md
```

---

## 4. File Content Blocks (Core)

Under `## 2. Contents`, each file is represented by one block:

### 4.1 Block Header (Mandatory)

```markdown
### N. `relative/path`
```

- `N` starts at 1 and increments globally.
- The path inside backticks is **relative to the root folder**, using `/`.
- The path must not be absolute and must not contain `..`.

### 4.2 Metadata (Optional)

```markdown
- name: `main.py`
- rel: `src/main.py`
- abs: `/Users/me/myproject/src/main.py`
- size: 1.23 KB
```

**Only the `### N. \`path\`` line is mandatory.** The restore process reads
that line and the code block beneath it.

### 4.3 Encoding Marker (Optional)

If the file is not UTF-8, add an HTML comment:

```markdown
<!-- encoding: gbk -->
```

The Chinese form `<!-- 文件编码：gbk -->` is also accepted.

### 4.4 Content (Mandatory)

Wrap content in a **code fence** with at least 3 backticks:

````markdown
```python
print("hello")
```
````

The language tag (`python`, `js`, etc.) is optional and ignored by the
restore process.
**If the file content itself contains runs of backticks, the fence must be
longer than the longest run.** For example, if the content has at most 3
consecutive backticks, use at least 4 for the fence.

### 4.5 Block Separator (Recommended)

End each file block with a line containing `---`:

```markdown
### 1. `README.md`

- name: `README.md`

```text
hello
```

---
```

---

## 5. Binary and Oversized Files

If a file is binary or too large, output a note instead of content:

```markdown
### 3. `logo.png`

- name: `logo.png`
- size: 12.34 KB

> binary file, no content exported.

---
```

During restore, such files are created as empty placeholders.

---

## 6. Complete Example

````markdown
# demo

- root: `/tmp/demo`
- exported: 2026-01-01 12:00:00
- files: 2
- folders: 1
- include_hidden: False
- max_file_mb: 10.0
- split_mb: 0

---

## 1. Tree

```
demo/
├── src/
│   └── main.py
└── README.md
```

---

## 2. Contents

### 1. `README.md`

- name: `README.md`
- rel: `README.md`
- abs: `/tmp/demo/README.md`
- size: 15 B

<!-- encoding: utf-8 -->

```text
# Demo
Hello, world!
```

---

### 2. `src/main.py`

- name: `main.py`
- rel: `src/main.py`
- abs: `/tmp/demo/src/main.py`
- size: 20 B

<!-- encoding: utf-8 -->

```python
print("hello world")
```

---
````

---

## 7. AI Output Checklist

- [ ] Top-level level-1 heading `# ...`
- [ ] Contains a `## 2. Contents` section (or Chinese equivalent)
- [ ] Each file starts with `### N. \`relative/path\``
- [ ] `N` increments from 1 without gaps
- [ ] Paths use forward slashes `/`, are not absolute, contain no `..`
- [ ] Content is wrapped in a code fence (at least 3 backticks)
- [ ] If the content contains backticks, the fence must be longer
- [ ] Binary / oversized files use `> note` instead of content
- [ ] Blocks are separated by `---`
- [ ] **Do not wrap the entire document in a code block**

---

## 8. Common Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Missing `### N. \`path\`` | File will not be restored | Add the block header |
| Absolute path | Rejected or path escape | Use a relative path |
| Fence too short | Content is truncated | Use a longer fence |
| Whole md wrapped in ``` | Cannot be parsed | Do not wrap the entire document |
| No `---` between blocks | Usually fine, but less readable | Add `---` |
| Path contains `..` | Rejected and skipped | Use a normal relative path |

---

## 9. Split Output (Optional)

For very long content, split into one mother file and several parts:

- **Mother file**: contains metadata, tree, and an index table:

  ```markdown
  | Part | Range | Count | Link |
  |:---|:---|---:|:---|
  | `xxx_part01.md` | 1 - 120 | 120 | [Open](./xxx_part01.md) |
  ```

- **Part files**: named `<mother_name>_partNN.md`, containing several
  `### N. \`path\`` blocks (numbering is globally continuous).
  The restore tool will auto-discover and merge all parts.
'''


# ==================== GUI ====================
class ExportTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folder_var = tk.StringVar()
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_size_var = tk.StringVar(value="10")
        self.split_size_var = tk.StringVar(value="5")
        self.cancel_event = threading.Event()
        self._build()

    def _build(self):
        row = ttk.Frame(self); row.pack(fill='x', pady=4)
        ttk.Label(row, text=tr('lbl_target_folder')).pack(side='left')
        ttk.Entry(row, textvariable=self.folder_var).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text=tr('btn_choose'),
                   command=self.choose_folder).pack(side='left')

        opts = ttk.LabelFrame(self, text=tr('frame_options'), padding=10)
        opts.pack(fill='x', pady=6)
        ttk.Checkbutton(opts, text=tr('chk_include_hidden'),
                        variable=self.include_hidden_var).pack(anchor='w')
        r1 = ttk.Frame(opts); r1.pack(fill='x', pady=(8, 0))
        ttk.Label(r1, text=tr('lbl_max_size')).pack(side='left')
        ttk.Entry(r1, textvariable=self.max_size_var, width=8).pack(side='left', padx=6)
        r2 = ttk.Frame(opts); r2.pack(fill='x', pady=(6, 0))
        ttk.Label(r2, text=tr('lbl_split_size')).pack(side='left')
        ttk.Entry(r2, textvariable=self.split_size_var, width=8).pack(side='left', padx=6)
        ttk.Label(r2, text=tr('lbl_split_hint'), foreground="#666").pack(side='left', padx=6)

        btn_row = ttk.Frame(self); btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text=tr('btn_start_export'),
                                    command=self.start)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(btn_row, text=tr('btn_cancel'),
                                     command=self.cancel, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        prog = ttk.LabelFrame(self, text=tr('frame_progress'), padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value=tr('status_ready'))
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=620, justify='left').pack(fill='x', pady=(8, 0))
        log_frame = ttk.Frame(prog); log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=sb.set, state='disabled')

    def choose_folder(self):
        p = filedialog.askdirectory(title=tr('lbl_target_folder'))
        if p:
            self.folder_var.set(p)

    def log_write(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _parse_float(self, s, default=0.0):
        s = (s or '').strip()
        if not s:
            return default
        v = float(s)
        if v < 0:
            raise ValueError
        return v

    def start(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning(tr('warn_title'), tr('warn_no_folder')); return
        root_path = Path(folder)
        if not root_path.is_dir():
            messagebox.showerror(tr('err_title'), tr('err_invalid_folder')); return
        try:
            max_mb = self._parse_float(self.max_size_var.get(), 10.0)
            split_mb = self._parse_float(self.split_size_var.get(), 0.0)
        except ValueError:
            messagebox.showerror(tr('err_title'), tr('err_size_param')); return

        out_path = filedialog.asksaveasfilename(
            title=tr('dlg_save_mother_title'),
            defaultextension=".md",
            initialfile=f"{root_path.name}_export.md",
            filetypes=[(tr('ft_md'), "*.md"), (tr('ft_all'), "*.*")],
        )
        if not out_path:
            return

        self.start_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.progress.configure(value=0, maximum=100)
        self.log.configure(state='normal'); self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.cancel_event.clear()

        threading.Thread(
            target=self._worker,
            args=(root_path, Path(out_path),
                  self.include_hidden_var.get(), max_mb, split_mb),
            daemon=True,
        ).start()

    def _worker(self, root_path, out_path, include_hidden, max_mb, split_mb):
        try:
            def cb(cur, total, name):
                step = max(1, total // 200) if total > 200 else 1
                if cur % step != 0 and cur != total:
                    return
                pct = (cur / total * 100) if total else 100.0
                self.after(0, lambda: self._update_progress(cur, total, name, pct))

            result = generate_markdown(
                root_path, out_path,
                include_hidden=include_hidden,
                max_size_mb=max_mb, split_size_mb=split_mb,
                progress_cb=cb, cancel_event=self.cancel_event,
            )
            self.after(0, lambda: self._done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.after(0, lambda: self._error(e, err))

    def _update_progress(self, cur, total, name, pct):
        self.progress.configure(value=pct)
        self.status_var.set(tr('status_progress', cur=cur, total=total, name=name))
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _done(self, r):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
        if r['split']:
            self.status_var.set(tr('status_done_split',
                                   files=r['files'], dirs=r['dirs'],
                                   parts=len(r['parts'])))
            self.log_write(tr('log_mother_file', path=r['output']))
            for p in r['parts']:
                self.log_write(tr('log_branch', path=p))
            messagebox.showinfo(tr('info_done_title'),
                tr('info_export_done_split',
                   files=r['files'], dirs=r['dirs'],
                   parts=len(r['parts']), path=r['output']))
        else:
            self.status_var.set(tr('status_done', files=r['files'], dirs=r['dirs']))
            self.log_write(tr('log_exported_to', path=r['output']))
            messagebox.showinfo(tr('info_done_title'),
                tr('info_export_done', files=r['files'], dirs=r['dirs'],
                   path=r['output']))

    def _error(self, e, err):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.status_var.set(tr('status_error'))
        self.log_write(err)
        messagebox.showerror(tr('err_title'), tr('err_export_failed', err=e))

    def cancel(self):
        self.cancel_event.set()
        self.status_var.set(tr('status_cancelling'))


class RestoreTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.md_paths = []
        self.target_var = tk.StringVar()
        self.auto_parts_var = tk.BooleanVar(value=True)
        self.cancel_event = threading.Event()
        self._build()

    def _build(self):
        ttk.Label(self, text=tr('lbl_restore_info'),
                  foreground="#555", wraplength=680,
                  justify='left').pack(fill='x', pady=(0, 8))

        row = ttk.Frame(self); row.pack(fill='x', pady=4)
        ttk.Button(row, text=tr('btn_choose_md'),
                   command=self.choose_md).pack(side='left')
        ttk.Button(row, text=tr('btn_clear_list'),
                   command=self.clear_md).pack(side='left', padx=6)
        self.count_var = tk.StringVar(value=tr('lbl_selected_count', n=0))
        ttk.Label(row, textvariable=self.count_var,
                  foreground="#666").pack(side='left', padx=8)

        list_frame = ttk.LabelFrame(self, text=tr('frame_selected_files'), padding=8)
        list_frame.pack(fill='both', expand=True, pady=6)
        self.file_list = tk.Listbox(list_frame, height=6)
        self.file_list.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(list_frame, command=self.file_list.yview)
        sb.pack(side='right', fill='y')
        self.file_list.configure(yscrollcommand=sb.set)

        row2 = ttk.Frame(self); row2.pack(fill='x', pady=6)
        ttk.Label(row2, text=tr('lbl_restore_to')).pack(side='left')
        ttk.Entry(row2, textvariable=self.target_var).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(row2, text=tr('btn_choose'),
                   command=self.choose_target).pack(side='left')

        ttk.Checkbutton(self, text=tr('chk_auto_discover'),
                        variable=self.auto_parts_var).pack(anchor='w', pady=4)

        btn_row = ttk.Frame(self); btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text=tr('btn_start_restore'),
                                    command=self.start)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(btn_row, text=tr('btn_cancel'),
                                     command=self.cancel, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        prog = ttk.LabelFrame(self, text=tr('frame_progress'), padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value=tr('status_ready'))
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=620, justify='left').pack(fill='x', pady=(8, 0))
        log_frame = ttk.Frame(prog); log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        sb2 = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb2.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=sb2.set, state='disabled')

    def choose_md(self):
        paths = filedialog.askopenfilenames(
            title=tr('dlg_choose_md_title'),
            filetypes=[(tr('ft_md'), "*.md"), (tr('ft_all'), "*.*")],
        )
        if paths:
            for p in paths:
                if p not in self.md_paths:
                    self.md_paths.append(p)
            self._refresh_list()

    def clear_md(self):
        self.md_paths.clear()
        self._refresh_list()

    def _refresh_list(self):
        self.file_list.delete(0, 'end')
        for p in self.md_paths:
            self.file_list.insert('end', p)
        self.count_var.set(tr('lbl_selected_count', n=len(self.md_paths)))

    def choose_target(self):
        p = filedialog.askdirectory(title=tr('dlg_choose_target_title'))
        if p:
            self.target_var.set(p)

    def log_write(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def start(self):
        if not self.md_paths:
            messagebox.showwarning(tr('warn_title'), tr('warn_no_md')); return
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning(tr('warn_title'), tr('warn_no_target')); return
        target_path = Path(target)
        target_path.mkdir(parents=True, exist_ok=True)

        if not messagebox.askyesno(tr('confirm_title'),
                                   tr('confirm_overwrite', path=target_path)):
            return

        self.start_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.progress.configure(value=0, maximum=100)
        self.log.configure(state='normal'); self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.cancel_event.clear()

        threading.Thread(
            target=self._worker,
            args=(list(self.md_paths), target_path, self.auto_parts_var.get()),
            daemon=True,
        ).start()

    def _worker(self, md_paths, target_path, auto_parts):
        try:
            def cb(cur, total, name):
                step = max(1, total // 200) if total > 200 else 1
                if cur % step != 0 and cur != total:
                    return
                pct = (cur / total * 100) if total else 100.0
                self.after(0, lambda: self._update_progress(cur, total, name, pct))

            result = restore_from_md(
                md_paths, target_path,
                auto_discover_parts=auto_parts,
                progress_cb=cb, cancel_event=self.cancel_event,
            )
            self.after(0, lambda: self._done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.after(0, lambda: self._error(e, err))

    def _update_progress(self, cur, total, name, pct):
        self.progress.configure(value=pct)
        self.status_var.set(tr('status_progress', cur=cur, total=total, name=name))
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _done(self, r):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
        self.status_var.set(tr('status_done_restore',
                               written=r['written'], total=r['total']))
        self.log_write(tr('log_restore_target', path=r['target']))
        self.log_write(tr('log_scanned_md'))
        for p in r['files_scanned']:
            self.log_write(tr('log_branch', path=p))
        if r['errors']:
            for e in r['errors']:
                self.log_write(tr('log_warn', msg=e))
        if r['skipped']:
            for s in r['skipped']:
                self.log_write(tr('log_skip', msg=s))

        skip_text = tr('skip_suffix', n=len(r['skipped'])) if r['skipped'] else ''
        messagebox.showinfo(tr('info_done_title'),
            tr('info_restore_done',
               path=r['target'], written=r['written'], total=r['total'],
               scanned=len(r['files_scanned']), skip=skip_text))

    def _error(self, e, err):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.status_var.set(tr('status_error'))
        self.log_write(err)
        messagebox.showerror(tr('err_title'), tr('err_restore_failed', err=e))

    def cancel(self):
        self.cancel_event.set()
        self.status_var.set(tr('status_cancelling'))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._build()

    def _build(self):
        for w in self.root.winfo_children():
            w.destroy()

        self.root.title(tr('app_title'))
        self.root.geometry("780x700")
        self.root.minsize(680, 600)

        toolbar = ttk.Frame(self.root, padding=(12, 8, 12, 0))
        toolbar.pack(fill='x')

        ttk.Label(toolbar, text=tr('lang_label')).pack(side='left')
        self.lang_var = tk.StringVar(value=LABEL_BY_LANG[CURRENT_LANG])
        self.lang_combo = ttk.Combobox(
            toolbar, textvariable=self.lang_var,
            values=[label for _, label in LANGS],
            state='readonly', width=14,
        )
        self.lang_combo.pack(side='left', padx=6)
        self.lang_combo.bind('<<ComboboxSelected>>', self._on_lang_change)

        ttk.Button(toolbar, text=tr('btn_gen_ai_guide'),
                   command=self.save_ai_guide).pack(side='right')

        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=8, pady=8)
        self.export_tab = ExportTab(nb)
        self.restore_tab = RestoreTab(nb)
        nb.add(self.export_tab, text=tr('tab_export'))
        nb.add(self.restore_tab, text=tr('tab_restore'))

    def _on_lang_change(self, event=None):
        global CURRENT_LANG
        label = self.lang_combo.get()
        code = LANG_BY_LABEL.get(label)
        if code and code != CURRENT_LANG:
            CURRENT_LANG = code
            self._build()

    def save_ai_guide(self):
        # 中文界面 → 中文规范；其他语言 → 英文规范
        if CURRENT_LANG == 'zh':
            guide_text = AI_GUIDE_MD
            default_name = 'AI输出规范_文件夹Markdown格式.md'
        else:
            guide_text = AI_GUIDE_MD_EN
            default_name = 'AI_Guide_Folder_Markdown_Format.md'

        out = filedialog.asksaveasfilename(
            title=tr('dlg_save_guide_title'),
            defaultextension=".md",
            initialfile=default_name,
            filetypes=[(tr('ft_md'), "*.md"), (tr('ft_all'), "*.*")],
        )
        if not out:
            return
        try:
            Path(out).write_text(guide_text, encoding='utf-8')
            messagebox.showinfo(tr('info_done_title'),
                                tr('info_guide_saved', path=out))
        except Exception as e:
            messagebox.showerror(tr('err_title'),
                                 tr('err_guide_save_failed', err=e))


def main():
    root = tk.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.2)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()