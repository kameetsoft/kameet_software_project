# # class YearwiseRouter:
# #     def db_for_read(self, model, **hints):
# #         if model._meta.app_label == 'accounts':
# #             year = hints.get('year')
# #             if year:
# #                 return f'fy_{year}'
# #         return 'default'

# #     def db_for_write(self, model, **hints):
# #         if model._meta.app_label == 'accounts':
# #             year = hints.get('year')
# #             if year:
# #                 return f'fy_{year}'
# #         return 'default'

# #     def allow_relation(self, obj1, obj2, **hints):
# #         return True

# #     def allow_migrate(self, db, app_label, model_name=None, **hints):
# #         if app_label == 'accounts':
# #             return db.startswith('fy_')
# #         return db == 'default'



# class YearwiseRouter:
#     def db_for_read(self, model, **hints):
#         if model._meta.model_name == 'dataentry':  # ✅ lowercase
#             year = hints.get('year')
#             if year:
#                 return f'fy_{year}'
#         return 'default'

#     def db_for_write(self, model, **hints):
#         if model._meta.model_name == 'dataentry':  # ✅ lowercase
#             year = hints.get('year')
#             if year:
#                 return f'fy_{year}'
#         return 'default'

#     def allow_relation(self, obj1, obj2, **hints):
#         return True

#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         if model_name == 'dataentry' and db.startswith('fy_'):  # ✅ lowercase
#             return True
#         elif model_name != 'dataentry' and db == 'default':
#             return True
#         return False



from datetime import date


class YearwiseRouter:
    def db_for_read(self, model, **hints):
        year = hints.get('year')
        if model._meta.app_label == 'accounts' and model._meta.model_name == 'dataentry':
            if year:
                return f'fy_{year}'
        return 'default'

    def db_for_write(self, model, **hints):
        year = hints.get('year')
        if model._meta.app_label == 'accounts' and model._meta.model_name == 'dataentry':
            if year:
                return f'fy_{year}'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'accounts':
            if db.startswith('fy_'):
                return True
        return db == 'default'



    from datetime import date

    def fiscal_year_range(fy_str):
        # Accept both "2024_25" and "2024-25"
        fy_str = fy_str.replace("_", "-")
        try:
            start_year, end_suffix = fy_str.split("-")
            start_year = int(start_year)
            end_year = int("20" + end_suffix) if len(end_suffix) == 2 else int(end_suffix)
        except Exception as e:
            raise ValueError(f"Invalid fiscal year format: {fy_str}") from e

        start_date = date(start_year, 4, 1)
        end_date = date(start_year + 1, 3, 31)
        return start_date, end_date
