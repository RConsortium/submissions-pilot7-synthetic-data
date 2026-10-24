#************************************************************************
# Purpose:     Additional functions used for table generation
# Input:       NA
# Output:      NA
#************************************************************************

format_percent <- function(x) {
  # Apply standard label_style_number formatting
  default_fmt <- label_style_number(digits = 0, width = 3, justify = "right", scale = 100)(x)

  # Replace values > 0 and < 0.01 (1%) with " <1"
  # Replace values > 0.99 and < 1 (100%) with " >99"
  # For values > 1 and < 9.5% add extra space at the beginning to align with other values
  ifelse(!is.na(x) & x > 0 & x < 0.01,
    " <1",
    ifelse(!is.na(x) & x > 0.99 & x < 1,
      " >99",
      ifelse(!is.na(x) & (x >= 0.01 & x < 0.095),
        paste0("\u2007", default_fmt),
        default_fmt
      )
    )
  )
}
